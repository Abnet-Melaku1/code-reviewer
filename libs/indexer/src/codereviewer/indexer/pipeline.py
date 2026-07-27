from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

import codereviewer.db.models as db_models
from codereviewer.indexer.chunker import chunk_code
from codereviewer.indexer.walker import walk_files
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
