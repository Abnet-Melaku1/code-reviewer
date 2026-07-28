from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import codereviewer.db.models as db_models
from codereviewer.api.config import ApiConfig
from codereviewer.api.webhooks import get_db_session
from codereviewer.github.client import HttpGitHubClient, MockGitHubClient
from codereviewer.schemas.enums import ReviewStatus
from codereviewer.schemas.models import PullRequest, Review, ReviewComment

router = APIRouter(prefix="/api/v1", tags=["reviews"])
config = ApiConfig()


@router.post("/pulls/{id}/reviews", response_model=Review, status_code=status.HTTP_201_CREATED)
async def create_review(
    id: int,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> Review:
    """Trigger a new code review run for a pull request."""
    # Ensure PR exists
    pr_stmt = select(db_models.PullRequest).where(db_models.PullRequest.id == id)
    pr_result = await session.execute(pr_stmt)
    db_pr = pr_result.scalars().first()
    if not db_pr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pull Request not found",
        )

    repo_stmt = select(db_models.Repository).where(db_models.Repository.id == db_pr.repository_id)
    repo_result = await session.execute(repo_stmt)
    db_repo = repo_result.scalars().first()
    if not db_repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    # Check if a review is already running to prevent duplicate jobs
    running_stmt = select(db_models.Review).where(
        db_models.Review.pull_request_id == id,
        db_models.Review.status == ReviewStatus.running,
    )
    running_result = await session.execute(running_stmt)
    if running_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A review run is already in progress for this PR.",
        )

    # Initialize a new Review run
    db_review = db_models.Review(
        pull_request_id=id,
        head_sha=db_pr.head_sha,
        status=ReviewStatus.queued,
        model="gpt-4o",
        must_fix=0,
        suggestions=0,
        nits=0,
        tokens_in=0,
        tokens_out=0,
        cost_cents=0,
        latency_ms=0,
    )
    session.add(db_review)
    await session.commit()
    await session.refresh(db_review)

    # Enqueue background review task
    arq_pool = request.app.state.arq_pool
    owner = db_repo.owner
    name = db_repo.name
    await arq_pool.enqueue_job(
        "review_pr",
        pull_request_id=db_pr.id,
        repository_id=db_repo.id,
        clone_url=f"https://github.com/{owner}/{name}.git",
        commit_sha=db_pr.head_sha,
        base_sha=db_pr.base_sha,
    )
    return db_review.to_schema()


def get_github_client(installation_id: int):

    """Retrieve either HttpGitHubClient or MockGitHubClient depending on config credentials."""
    if config.github_app_id and config.github_private_key:
        return HttpGitHubClient(
            app_id=config.github_app_id,
            private_key=config.github_private_key,
            installation_id=installation_id,
        )
    return MockGitHubClient()


@router.get("/repositories/{id}/pulls", response_model=list[PullRequest])
async def list_pulls(id: int, session: AsyncSession = Depends(get_db_session)) -> list[PullRequest]:
    """List all pull requests registered for a specific repository."""
    # Ensure repository exists
    repo_stmt = select(db_models.Repository).where(db_models.Repository.id == id)
    repo_result = await session.execute(repo_stmt)
    if not repo_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    stmt = select(db_models.PullRequest).where(db_models.PullRequest.repository_id == id)
    result = await session.execute(stmt)
    pulls = result.scalars().all()
    return [p.to_schema() for p in pulls]


@router.get("/pulls/{id}/reviews", response_model=list[Review])
async def list_reviews(id: int, session: AsyncSession = Depends(get_db_session)) -> list[Review]:
    """List all review runs for a pull request."""
    # Ensure PR exists
    pr_stmt = select(db_models.PullRequest).where(db_models.PullRequest.id == id)
    pr_result = await session.execute(pr_stmt)
    if not pr_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pull Request not found",
        )

    stmt = select(db_models.Review).where(db_models.Review.pull_request_id == id)
    result = await session.execute(stmt)
    reviews = result.scalars().all()
    return [r.to_schema() for r in reviews]


@router.get("/reviews/{id}", response_model=Review)
async def get_review(id: int, session: AsyncSession = Depends(get_db_session)) -> Review:
    """Get the status and summary metrics of a specific review run."""
    stmt = select(db_models.Review).where(db_models.Review.id == id)
    result = await session.execute(stmt)
    review = result.scalars().first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )
    return review.to_schema()


@router.get("/reviews/{id}/comments", response_model=list[ReviewComment])
async def get_review_comments(
    id: int,
    session: AsyncSession = Depends(get_db_session),
) -> list[ReviewComment]:
    """Get all inline review comments produced by a specific review run."""
    # Ensure review exists
    review_stmt = select(db_models.Review).where(db_models.Review.id == id)
    review_result = await session.execute(review_stmt)
    if not review_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    stmt = select(db_models.ReviewComment).where(db_models.ReviewComment.review_id == id)
    result = await session.execute(stmt)
    comments = result.scalars().all()
    return [c.to_schema() for c in comments]


@router.post("/reviews/{id}/rerun", status_code=status.HTTP_202_ACCEPTED)
async def rerun_review(
    id: int,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Manually trigger a re-run of a specific review, idempotent per (pr, head_sha)."""
    stmt = select(db_models.Review).where(db_models.Review.id == id)
    result = await session.execute(stmt)
    db_review = result.scalars().first()
    if not db_review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    pr_stmt = select(db_models.PullRequest).where(
        db_models.PullRequest.id == db_review.pull_request_id
    )
    pr_result = await session.execute(pr_stmt)
    db_pr = pr_result.scalars().first()
    if not db_pr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pull Request not found",
        )

    repo_stmt = select(db_models.Repository).where(db_models.Repository.id == db_pr.repository_id)
    repo_result = await session.execute(repo_stmt)
    db_repo = repo_result.scalars().first()
    if not db_repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    arq_pool = request.app.state.arq_pool
    owner = db_repo.owner
    name = db_repo.name
    await arq_pool.enqueue_job(
        "review_pr",
        pull_request_id=db_pr.id,
        repository_id=db_repo.id,
        clone_url=f"https://github.com/{owner}/{name}.git",
        commit_sha=db_pr.head_sha,
        base_sha=db_pr.base_sha,
    )
    return {"status": "enqueued"}


@router.post("/reviews/{id}/post")
async def post_review_to_github(
    id: int,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str | int]:
    """Publish a review's inline comments directly to the GitHub PR.

    Enforces S2: raises HTTP 403 Forbidden if posting_enabled is False.
    """
    stmt = select(db_models.Review).where(db_models.Review.id == id)
    result = await session.execute(stmt)
    db_review = result.scalars().first()
    if not db_review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    pr_stmt = select(db_models.PullRequest).where(
        db_models.PullRequest.id == db_review.pull_request_id
    )
    pr_result = await session.execute(pr_stmt)
    db_pr = pr_result.scalars().first()
    if not db_pr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pull Request not found",
        )

    repo_stmt = select(db_models.Repository).where(db_models.Repository.id == db_pr.repository_id)
    repo_result = await session.execute(repo_stmt)
    db_repo = repo_result.scalars().first()
    if not db_repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    # Security Guardrail S2: posting must be enabled for the repository
    if not db_repo.posting_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Posting reviews is disabled for this repository.",
        )

    # Load all comments for this review
    comments_stmt = select(db_models.ReviewComment).where(db_models.ReviewComment.review_id == id)
    comments_result = await session.execute(comments_stmt)
    db_comments = comments_result.scalars().all()

    if not db_comments:
        return {"status": "skipped", "reason": "No comments to post"}

    # Format comments for the GitHub API reviews call
    github_comments = []
    for c in db_comments:
        body_text = c.body
        if c.suggested_patch:
            body_text += f"\n\n```suggestion\n{c.suggested_patch}\n```"

        if c.citations:
            body_text += "\n\n---\n*Grounded in:* "
            citations_text = []
            for cit in c.citations:
                if cit.kind == "diff_hunk" and cit.diff_ref:
                    citations_text.append(f"diff hunk (`{cit.diff_ref}`)")
                elif cit.kind == "code_chunk" and cit.code_chunk_id:
                    citations_text.append(f"code chunk #{cit.code_chunk_id}")
                elif cit.kind == "convention" and cit.convention_id:
                    citations_text.append(f"convention #{cit.convention_id}")
            body_text += ", ".join(citations_text)

        github_comments.append(
            {
                "path": c.file_path,
                "line": c.line,
                "side": c.side.value.upper(),
                "body": body_text,
            }
        )

    github_client = get_github_client(db_repo.github_installation_id)
    review_id = await github_client.post_pr_review(
        owner=db_repo.owner,
        repo=db_repo.name,
        pr_number=db_pr.number,
        commit_sha=db_review.head_sha,
        comments=github_comments,
        body=db_review.summary or "CodeReviewer.ai Review Completed",
    )

    # Update comments in database to record they've been posted
    for c in db_comments:
        c.posted_to_github = True
    await session.commit()

    return {"status": "posted", "github_review_id": review_id}
