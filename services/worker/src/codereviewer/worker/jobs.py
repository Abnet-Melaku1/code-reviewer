import shutil
import subprocess
import tempfile
from typing import Any

import codereviewer.db.session as db_session
from codereviewer.indexer.pipeline import index_repository_delta, index_repository_files
from codereviewer.providers.base import EmbeddingsProvider
from codereviewer.providers.fake import FakeEmbeddingsProvider
from codereviewer.providers.openai import OpenAIEmbeddingsProvider
from codereviewer.providers.voyage import VoyageEmbeddingsProvider
from codereviewer.worker.config import WorkerConfig

config = WorkerConfig()


def get_embeddings_provider() -> EmbeddingsProvider:
    """Instantiate the embeddings provider based on worker configuration."""
    provider_name = config.embeddings_provider.lower()
    if provider_name == "voyage":
        return VoyageEmbeddingsProvider(
            api_key=config.voyage_api_key, model_name=config.embeddings_model
        )
    elif provider_name == "openai":
        return OpenAIEmbeddingsProvider(
            api_key=config.openai_api_key, model_name=config.embeddings_model
        )
    else:
        return FakeEmbeddingsProvider()


def clone_repository(clone_url: str, dest_path: str) -> None:
    """Clone repository using standard git CLI subprocess."""
    subprocess.run(
        ["git", "clone", clone_url, dest_path],
        check=True,
        capture_output=True,
    )


async def index_repo(
    ctx: Any,
    repository_id: int,
    clone_url: str,
    commit_sha: str,
    base_sha: str | None = None,
) -> None:
    """arq job that indexes a repository.

    Clones the repository at clone_url to a temporary directory, initializes
    the database engine and embeddings provider, and executes either the full
    or delta indexing pipeline.
    """
    provider = get_embeddings_provider()

    # Initialize database connections
    engine = db_session.make_engine(config.database_url)
    session_factory = db_session.create_session_factory(engine)

    # Create temporary path for repository checkout
    temp_dir = tempfile.mkdtemp()
    try:
        clone_repository(clone_url, temp_dir)

        # Run pipeline transactionally
        async with db_session.session_scope(session_factory) as session:
            if base_sha:
                await index_repository_delta(
                    session=session,
                    repo_path=temp_dir,
                    repository_id=repository_id,
                    provider=provider,
                    base_sha=base_sha,
                    head_sha=commit_sha,
                )
            else:
                await index_repository_files(
                    session=session,
                    repo_path=temp_dir,
                    repository_id=repository_id,
                    provider=provider,
                    commit_sha=commit_sha,
                )
            await session.commit()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        await engine.dispose()
