from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import codereviewer.db.models as db_models
from codereviewer.providers.base import EmbeddingsProvider
from codereviewer.schemas.models import (
    CodeChunk as SchemaCodeChunk,
)
from codereviewer.schemas.models import (
    Convention as SchemaConvention,
)
from codereviewer.schemas.models import (
    DiffHunk,
    RetrievedContext,
)


class Retriever:
    """RAG context retriever for code review grounding."""

    def __init__(self, session: AsyncSession, provider: EmbeddingsProvider):
        self.session = session
        self.provider = provider

    async def retrieve_context(
        self, repository_id: int, hunk: DiffHunk, limit: int = 5
    ) -> RetrievedContext:
        """Retrieve similar chunks and conventions to ground the review of a diff hunk."""
        # 1. Compute embedding of the hunk content
        hunk_vectors = await self.provider.embed_texts([hunk.content])
        hunk_vector = hunk_vectors[0]

        # 2. Query similar chunks from the database (supporting SQLite fallback for tests)
        db_chunks = []
        if self.session.bind and self.session.bind.dialect.name == "sqlite":
            result = await self.session.execute(
                select(db_models.CodeChunk)
                .join(db_models.IndexedFile)
                .where(db_models.IndexedFile.repository_id == repository_id)
                .limit(limit)
            )
            db_chunks = list(result.scalars().all())
        else:
            result = await self.session.execute(
                select(db_models.CodeChunk)
                .join(db_models.IndexedFile)
                .where(db_models.IndexedFile.repository_id == repository_id)
                .order_by(db_models.CodeChunk.embedding.cosine_distance(hunk_vector))
                .limit(limit)
            )
            db_chunks = list(result.scalars().all())

        # Map DB chunks to schema CodeChunks
        schema_chunks = [
            SchemaCodeChunk(
                id=chunk.id,
                symbol_kind=chunk.symbol_kind,
                symbol_name=chunk.symbol_name,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                content=chunk.content,
                token_count=chunk.token_count,
            )
            for chunk in db_chunks
        ]

        # 3. Retrieve active conventions
        conv_result = await self.session.execute(
            select(db_models.Convention).where(
                db_models.Convention.repository_id == repository_id,
                db_models.Convention.active,
            )
        )
        db_conventions: list[db_models.Convention] = list(conv_result.scalars().all())

        schema_conventions = [
            SchemaConvention(
                id=conv.id,
                title=conv.title,
                description=conv.description,
                example_code=conv.example_code,
                source=conv.source,
                confidence=conv.confidence,
                active=conv.active,
            )
            for conv in db_conventions
        ]

        return RetrievedContext(chunks=schema_chunks, conventions=schema_conventions)
