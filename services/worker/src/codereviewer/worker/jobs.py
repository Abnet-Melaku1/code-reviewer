import contextlib
import shutil
import subprocess
import tempfile
from typing import Any

from sqlalchemy import desc, select

import codereviewer.db.models as db_models
import codereviewer.db.session as db_session
from codereviewer.indexer.pipeline import index_repository_delta, index_repository_files
from codereviewer.providers.base import EmbeddingsProvider, LlmProvider
from codereviewer.providers.fake import FakeEmbeddingsProvider, FakeLlmProvider
from codereviewer.providers.openai import OpenAIEmbeddingsProvider, OpenAiLlmProvider
from codereviewer.providers.voyage import VoyageEmbeddingsProvider
from codereviewer.retrieval.retriever import Retriever
from codereviewer.reviewer.agent import run_review
from codereviewer.reviewer.analyzers import register_default_analyzers
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


def get_llm_provider() -> LlmProvider:
    """Instantiate the LLM provider based on worker configuration."""
    provider_name = config.llm_provider.lower()
    if provider_name == "openai":
        return OpenAiLlmProvider(api_key=config.openai_api_key, model_name=config.llm_model)
    else:
        return FakeLlmProvider()


def clone_repository(clone_url: str, dest_path: str) -> None:
    """Clone repository using standard git CLI subprocess."""
    subprocess.run(
        ["git", "clone", clone_url, dest_path],
        check=True,
        capture_output=True,
    )


async def _pub_event(ctx: Any, event: Any) -> None:
    """Helper to publish a WebSocket schema event to the Redis pub/sub channel."""
    redis = ctx.get("redis") if ctx else None
    if redis:
        with contextlib.suppress(Exception):
            await redis.publish("codereviewer:events", event.model_dump_json())


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
    import codereviewer.schemas as schemas

    await _pub_event(
        ctx,
        schemas.IndexStatusEvent(
            repository_id=repository_id,
            index_status=schemas.IndexStatus.indexing,
        ),
    )

    await _pub_event(
        ctx,
        schemas.IndexProgressEvent(
            repository_id=repository_id,
            phase="Cloning repository...",
            files_done=0,
            files_total=5,
        ),
    )

    provider = get_embeddings_provider()

    # Initialize database connections
    engine = db_session.make_engine(config.database_url)
    session_factory = db_session.create_session_factory(engine)

    # Create temporary path for repository checkout
    temp_dir = tempfile.mkdtemp()
    try:
        clone_repository(clone_url, temp_dir)

        await _pub_event(
            ctx,
            schemas.IndexProgressEvent(
                repository_id=repository_id,
                phase="Running code-chunk extraction & embedding...",
                files_done=2,
                files_total=5,
            ),
        )

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

        await _pub_event(
            ctx,
            schemas.IndexProgressEvent(
                repository_id=repository_id,
                phase="Indexing complete. Saved embeddings.",
                files_done=5,
                files_total=5,
            ),
        )

        await _pub_event(
            ctx,
            schemas.IndexStatusEvent(
                repository_id=repository_id,
                index_status=schemas.IndexStatus.ready,
            ),
        )
    except Exception as e:
        # DB rollback is handled by session_scope; mark repo status as error
        try:
            async with db_session.session_scope(session_factory) as session:
                res = await session.execute(
                    select(db_models.Repository).where(db_models.Repository.id == repository_id)
                )
                repo = res.scalars().first()
                if repo:
                    repo.index_status = schemas.IndexStatus.error
                await session.commit()
        except Exception:
            pass

        await _pub_event(
            ctx,
            schemas.IndexStatusEvent(
                repository_id=repository_id,
                index_status=schemas.IndexStatus.error,
            ),
        )
        raise e
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        await engine.dispose()


async def review_pr(
    ctx: Any,
    pull_request_id: int,
    repository_id: int,
    clone_url: str,
    commit_sha: str,
    base_sha: str,
) -> None:
    """arq job that executes a code review on a pull request.

    Clones the repository at clone_url to a temporary directory, computes
    the git diff between base_sha and commit_sha, and executes the run_review
    agent pipeline transactionally.
    """
    provider = get_embeddings_provider()
    llm = get_llm_provider()

    # Initialize database engine and session factory
    engine = db_session.make_engine(config.database_url)
    session_factory = db_session.create_session_factory(engine)

    # Create temporary path for repository checkout
    temp_dir = tempfile.mkdtemp()
    try:
        clone_repository(clone_url, temp_dir)

        # Compute git diff locally (three-dot diff: merge base of base and head, to head)
        diff_result = subprocess.run(
            ["git", "diff", f"{base_sha}...{commit_sha}"],
            cwd=temp_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        diff_content = diff_result.stdout

        redis_client = ctx.get("redis") if ctx else None

        async with db_session.session_scope(session_factory) as session:
            retriever = Retriever(session, provider)
            # Register analyzers
            register_default_analyzers(llm)
            # Execute review pipeline
            if redis_client is not None:
                await run_review(
                    session=session,
                    provider=llm,
                    retriever=retriever,
                    pull_request_id=pull_request_id,
                    repository_id=repository_id,
                    diff_content=diff_content,
                    commit_sha=commit_sha,
                    model_name=config.llm_model,
                    redis_client=redis_client,
                )
            else:
                await run_review(
                    session=session,
                    provider=llm,
                    retriever=retriever,
                    pull_request_id=pull_request_id,
                    repository_id=repository_id,
                    diff_content=diff_content,
                    commit_sha=commit_sha,
                    model_name=config.llm_model,
                )
            await session.commit()
    except Exception as e:
        # Publish review.failed if a redis_client is present
        import codereviewer.schemas as schemas

        # We try to get the active review record for the PR to send review.failed
        try:
            async with db_session.session_scope(session_factory) as session:
                res = await session.execute(
                    select(db_models.Review)
                    .where(db_models.Review.pull_request_id == pull_request_id)
                    .order_by(desc(db_models.Review.id))
                )
                db_review = res.scalars().first()
                if db_review:
                    db_review.status = schemas.ReviewStatus.failed
                    await session.commit()
                    await _pub_event(
                        ctx,
                        schemas.ReviewFailedEvent(
                            review_id=db_review.id or 0,
                            error=str(e),
                        ),
                    )
        except Exception:
            pass
        raise e
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        await engine.dispose()
