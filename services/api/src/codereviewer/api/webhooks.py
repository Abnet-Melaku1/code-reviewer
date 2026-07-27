import json
from collections.abc import AsyncGenerator

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import codereviewer.db.models as db_models
import codereviewer.db.session as db_session
from codereviewer.api.config import ApiConfig
from codereviewer.github.client import verify_signature
from codereviewer.schemas.enums import IndexStatus, PullRequestState

router = APIRouter(tags=["webhooks"])
config = ApiConfig()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection to provide clean database sessions."""
    engine = db_session.make_engine(config.database_url)
    factory = db_session.create_session_factory(engine)
    async with db_session.session_scope(factory) as session:
        yield session
    await engine.dispose()


async def verify_github_signature(
    request: Request,
    x_hub_signature_256: str = Header(default=""),
) -> bytes:
    """FastAPI dependency that enforces strict signature HMAC verification."""
    body = await request.body()
    if not x_hub_signature_256:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing signature header",
        )

    if not verify_signature(config.github_webhook_secret, x_hub_signature_256, body):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
        )

    return body


@router.post("/webhooks/github", status_code=202)
async def handle_github_webhook(
    body: bytes = Depends(verify_github_signature),
    x_github_event: str = Header(default=""),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Intake endpoint receiving GitHub App webhooks and enqueuing worker jobs."""
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        ) from None

    redis = await create_pool(RedisSettings.from_dsn(config.redis_url))

    try:
        if x_github_event == "installation":
            action = payload.get("action")
            installation_id = payload["installation"]["id"]
            if action == "created":
                for repo_data in payload.get("repositories", []):
                    owner, name = repo_data["full_name"].split("/")
                    repo_stmt = select(db_models.Repository).where(
                        db_models.Repository.owner == owner,
                        db_models.Repository.name == name,
                    )
                    repo_result = await session.execute(repo_stmt)
                    db_repo = repo_result.scalars().first()
                    if not db_repo:
                        db_repo = db_models.Repository(
                            github_installation_id=installation_id,
                            owner=owner,
                            name=name,
                            default_branch="main",
                            index_status=IndexStatus.pending,
                        )
                        session.add(db_repo)
                        await session.flush()

                    await redis.enqueue_job(
                        "index_repo",
                        repository_id=db_repo.id,
                        clone_url=f"https://github.com/{owner}/{name}.git",
                        commit_sha="HEAD",
                    )
            elif action == "deleted":
                del_stmt = select(db_models.Repository).where(
                    db_models.Repository.github_installation_id == installation_id
                )
                del_result = await session.execute(del_stmt)
                for del_repo in del_result.scalars().all():
                    await session.delete(del_repo)

        elif x_github_event == "installation_repositories":
            action = payload.get("action")
            installation_id = payload["installation"]["id"]
            if action == "added":
                for repo_data in payload.get("repositories_added", []):
                    owner, name = repo_data["full_name"].split("/")
                    add_stmt = select(db_models.Repository).where(
                        db_models.Repository.owner == owner,
                        db_models.Repository.name == name,
                    )
                    add_result = await session.execute(add_stmt)
                    db_repo = add_result.scalars().first()
                    if not db_repo:
                        db_repo = db_models.Repository(
                            github_installation_id=installation_id,
                            owner=owner,
                            name=name,
                            default_branch="main",
                            index_status=IndexStatus.pending,
                        )
                        session.add(db_repo)
                        await session.flush()

                    await redis.enqueue_job(
                        "index_repo",
                        repository_id=db_repo.id,
                        clone_url=f"https://github.com/{owner}/{name}.git",
                        commit_sha="HEAD",
                    )
            elif action == "removed":
                for repo_data in payload.get("repositories_removed", []):
                    owner, name = repo_data["full_name"].split("/")
                    rem_stmt = select(db_models.Repository).where(
                        db_models.Repository.owner == owner,
                        db_models.Repository.name == name,
                    )
                    rem_result = await session.execute(rem_stmt)
                    db_repo = rem_result.scalars().first()
                    if db_repo:
                        await session.delete(db_repo)

        elif x_github_event == "push":
            ref = payload.get("ref", "")
            repo_data = payload.get("repository", {})
            full_name = repo_data.get("full_name", "")
            default_branch = repo_data.get("default_branch", "")

            if ref == f"refs/heads/{default_branch}" and full_name:
                owner, name = full_name.split("/")
                push_stmt = select(db_models.Repository).where(
                    db_models.Repository.owner == owner,
                    db_models.Repository.name == name,
                )
                push_result = await session.execute(push_stmt)
                db_repo = push_result.scalars().first()
                if db_repo:
                    before = payload.get("before")
                    after = payload.get("after")
                    base_sha = None
                    if before and before != "0000000000000000000000000000000000000000":
                        base_sha = before

                    await redis.enqueue_job(
                        "index_repo",
                        repository_id=db_repo.id,
                        clone_url=f"https://github.com/{owner}/{name}.git",
                        commit_sha=after,
                        base_sha=base_sha,
                    )

        elif x_github_event == "pull_request":
            action = payload.get("action")
            if action in ("opened", "synchronize", "reopened"):
                pr_data = payload.get("pull_request", {})
                repo_data = payload.get("repository", {})
                full_name = repo_data.get("full_name", "")

                if full_name:
                    owner, name = full_name.split("/")
                    pr_repo_stmt = select(db_models.Repository).where(
                        db_models.Repository.owner == owner,
                        db_models.Repository.name == name,
                    )
                    pr_repo_result = await session.execute(pr_repo_stmt)
                    db_repo = pr_repo_result.scalars().first()
                    if db_repo:
                        number = pr_data["number"]
                        head_sha = pr_data["head"]["sha"]
                        base_sha = pr_data["base"]["sha"]
                        title = pr_data["title"]
                        author = pr_data["user"]["login"]

                        pr_stmt = select(db_models.PullRequest).where(
                            db_models.PullRequest.repository_id == db_repo.id,
                            db_models.PullRequest.number == number,
                        )
                        pr_result = await session.execute(pr_stmt)
                        db_pr = pr_result.scalars().first()
                        if not db_pr:
                            db_pr = db_models.PullRequest(
                                repository_id=db_repo.id,
                                number=number,
                                head_sha=head_sha,
                                base_sha=base_sha,
                                title=title,
                                author=author,
                                state=PullRequestState.open,
                            )
                            session.add(db_pr)
                        else:
                            db_pr.head_sha = head_sha
                            db_pr.base_sha = base_sha
                            db_pr.title = title
                            db_pr.state = PullRequestState.open
                        await session.flush()

                        await redis.enqueue_job(
                            "review_pr",
                            pull_request_id=db_pr.id,
                            repository_id=db_repo.id,
                            clone_url=f"https://github.com/{owner}/{name}.git",
                            commit_sha=head_sha,
                            base_sha=base_sha,
                        )
            elif action == "closed":
                pr_data = payload.get("pull_request", {})
                repo_data = payload.get("repository", {})
                full_name = repo_data.get("full_name", "")
                if full_name:
                    owner, name = full_name.split("/")
                    close_repo_stmt = select(db_models.Repository).where(
                        db_models.Repository.owner == owner,
                        db_models.Repository.name == name,
                    )
                    close_repo_result = await session.execute(close_repo_stmt)
                    db_repo = close_repo_result.scalars().first()
                    if db_repo:
                        number = pr_data["number"]
                        close_pr_stmt = select(db_models.PullRequest).where(
                            db_models.PullRequest.repository_id == db_repo.id,
                            db_models.PullRequest.number == number,
                        )
                        close_pr_result = await session.execute(close_pr_stmt)
                        db_pr = close_pr_result.scalars().first()
                        if db_pr:
                            db_pr.state = PullRequestState.closed

        await session.commit()
    finally:
        await redis.close()

    return {"status": "enqueued"}
