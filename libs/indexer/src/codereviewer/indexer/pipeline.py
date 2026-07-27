import os
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

import codereviewer.db.models as db_models
from codereviewer.indexer.chunker import chunk_code
from codereviewer.indexer.git import get_file_delta
from codereviewer.indexer.walker import (
    LANGUAGE_EXTENSIONS,
    FileCandidate,
    compute_git_blob_sha,
    walk_files,
)
from codereviewer.providers.base import EmbeddingsProvider
from codereviewer.schemas.enums import IndexStatus


async def infer_conventions(session: AsyncSession, repository_id: int) -> None:
    """Infer coding conventions from the indexed repository (currently a placeholder stub).

    If no conventions exist for the repository, insert a default active convention.
    """
    from codereviewer.schemas.enums import ConventionSource

    result = await session.execute(
        select(db_models.Convention).where(db_models.Convention.repository_id == repository_id)
    )
    existing = result.scalars().all()
    if not existing:
        placeholder = db_models.Convention(
            repository_id=repository_id,
            title="CodeReviewer Default Style",
            description="Use explicit typing and descriptive names across the codebase.",
            example_code=(
                "def calculate_total(price: float, tax: float) -> float:\n    return price + tax"
            ),
            source=ConventionSource.inferred,
            confidence=0.8,
            active=True,
        )
        session.add(placeholder)


async def index_repository_files(
    session: AsyncSession,
    repo_path: str,
    repository_id: int,
    provider: EmbeddingsProvider,
    commit_sha: str,
) -> None:
    """Build the index for a repository from scratch.

    Walks files, chunks them, computes their embeddings, stores the files and chunks
    to pgvector transactionally, runs convention inference, and marks the repo as ready.
    """
    # 1. Update status to indexing
    result = await session.execute(
        select(db_models.Repository).where(db_models.Repository.id == repository_id)
    )
    repo = result.scalar_one()
    repo.index_status = IndexStatus.indexing
    await session.flush()

    # 2. Walk and chunk all source files
    candidates = walk_files(repo_path)

    all_chunks_to_embed = []
    chunk_to_candidate = []

    for candidate in candidates:
        file_chunks = chunk_code(candidate.content, candidate.language, candidate.path)
        for chunk in file_chunks:
            all_chunks_to_embed.append(chunk)
            chunk_to_candidate.append(candidate)

    # 3. Batch generate embeddings (batch size = 128 to stay within model limits)
    batch_size = 128
    embeddings = []
    for i in range(0, len(all_chunks_to_embed), batch_size):
        batch = all_chunks_to_embed[i : i + batch_size]
        texts = [c.content for c in batch]
        batch_embeddings = await provider.embed_texts(texts)
        embeddings.extend(batch_embeddings)

    # 4. Clear any existing indexed files (and cascading chunks) for the repository
    await session.execute(
        delete(db_models.IndexedFile).where(db_models.IndexedFile.repository_id == repository_id)
    )

    # 5. Insert new files and chunks
    # Map candidates to their corresponding DB IndexedFile object
    file_map = {}
    for candidate in candidates:
        db_file = db_models.IndexedFile(
            repository_id=repository_id,
            path=candidate.path,
            language=candidate.language,
            blob_sha=candidate.blob_sha,
            chunk_count=0,
        )
        session.add(db_file)
        file_map[candidate.path] = db_file

    # Flush so that db_file IDs are generated
    await session.flush()

    # Create and add CodeChunk DB records
    for chunk, candidate, embedding in zip(
        all_chunks_to_embed, chunk_to_candidate, embeddings, strict=True
    ):
        db_file = file_map[candidate.path]
        db_chunk = db_models.CodeChunk(
            indexed_file_id=db_file.id,
            symbol_kind=chunk.symbol_kind,
            symbol_name=chunk.symbol_name,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
            content=chunk.content,
            embedding=embedding,
            token_count=chunk.token_count,
        )
        session.add(db_chunk)
        db_file.chunk_count += 1

    # 6. Run convention inference
    await infer_conventions(session, repository_id)

    # 7. Complete index state
    repo.index_status = IndexStatus.ready
    repo.indexed_commit_sha = commit_sha
    repo.last_indexed_at = datetime.now(UTC)


async def index_repository_delta(
    session: AsyncSession,
    repo_path: str,
    repository_id: int,
    provider: EmbeddingsProvider,
    base_sha: str,
    head_sha: str,
) -> None:
    """Incrementally update the index of a repository based on changes.

    Computes file delta (added, modified, deleted). Deletes DB representations of
    deleted/modified files. Reads, chunks, and embeds newly added or modified files,
    then inserts them. Advances repository indexed commit to head_sha.
    """
    # 1. Update status to indexing
    result = await session.execute(
        select(db_models.Repository).where(db_models.Repository.id == repository_id)
    )
    repo = result.scalar_one()
    repo.index_status = IndexStatus.indexing
    await session.flush()

    # 2. Get git file delta
    delta = get_file_delta(repo_path, base_sha, head_sha)
    if not delta:
        # No changes to apply, advance commit and exit
        repo.index_status = IndexStatus.ready
        repo.indexed_commit_sha = head_sha
        repo.last_indexed_at = datetime.now(UTC)
        return

    # Separate deleted/modified paths and added/modified paths
    deleted_paths = [path for path, status in delta.items() if status in ("D", "M")]
    added_or_modified_paths = [path for path, status in delta.items() if status in ("A", "M")]

    # 3. Delete DB representation of deleted/modified files (cascading deletes their chunks)
    if deleted_paths:
        await session.execute(
            delete(db_models.IndexedFile).where(
                db_models.IndexedFile.repository_id == repository_id,
                db_models.IndexedFile.path.in_(deleted_paths),
            )
        )
        await session.flush()

    # 4. Process new/modified files
    candidates = []
    for path in added_or_modified_paths:
        full_path = os.path.join(repo_path, path)
        if not os.path.exists(full_path):
            continue

        ext = os.path.splitext(path)[1].lower()
        if ext not in LANGUAGE_EXTENSIONS:
            continue

        # Check if binary (via null byte scanning)
        try:
            with open(full_path, "rb") as f:
                binary_chunk = f.read(1024)
                if b"\0" in binary_chunk:
                    continue
        except OSError:
            continue

        # Read text content
        try:
            with open(full_path, encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError:
            continue

        language = LANGUAGE_EXTENSIONS[ext]
        blob_sha = compute_git_blob_sha(content.encode("utf-8"))

        candidates.append(
            FileCandidate(
                path=path,
                language=language,
                blob_sha=blob_sha,
                content=content,
            )
        )

    # 5. Chunk and batch embed
    all_chunks_to_embed = []
    chunk_to_candidate = []

    for candidate in candidates:
        file_chunks = chunk_code(candidate.content, candidate.language, candidate.path)
        for chunk in file_chunks:
            all_chunks_to_embed.append(chunk)
            chunk_to_candidate.append(candidate)

    if all_chunks_to_embed:
        # Batch generate embeddings (batch size = 128)
        batch_size = 128
        embeddings = []
        for i in range(0, len(all_chunks_to_embed), batch_size):
            batch = all_chunks_to_embed[i : i + batch_size]
            texts = [c.content for c in batch]
            batch_embeddings = await provider.embed_texts(texts)
            embeddings.extend(batch_embeddings)

        # 6. Insert new files and chunks
        file_map = {}
        for candidate in candidates:
            db_file = db_models.IndexedFile(
                repository_id=repository_id,
                path=candidate.path,
                language=candidate.language,
                blob_sha=candidate.blob_sha,
                chunk_count=0,
            )
            session.add(db_file)
            file_map[candidate.path] = db_file

        # Flush to get file IDs
        await session.flush()

        for chunk, candidate, embedding in zip(
            all_chunks_to_embed, chunk_to_candidate, embeddings, strict=True
        ):
            db_file = file_map[candidate.path]
            db_chunk = db_models.CodeChunk(
                indexed_file_id=db_file.id,
                symbol_kind=chunk.symbol_kind,
                symbol_name=chunk.symbol_name,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                content=chunk.content,
                embedding=embedding,
                token_count=chunk.token_count,
            )
            session.add(db_chunk)
            db_file.chunk_count += 1

    # 7. Run convention inference
    await infer_conventions(session, repository_id)

    # 8. Update Repository state
    repo.index_status = IndexStatus.ready
    repo.indexed_commit_sha = head_sha
    repo.last_indexed_at = datetime.now(UTC)
