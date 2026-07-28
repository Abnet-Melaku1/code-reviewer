from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import codereviewer.db.models as db_models
from codereviewer.api.webhooks import get_db_session
from codereviewer.schemas.enums import ConventionSource, IndexStatus
from codereviewer.schemas.models import Convention, Repository
from codereviewer.schemas.requests import (
    ConventionCreate,
    ConventionUpdate,
    RepositoryCreate,
    RepositoryUpdate,
)

router = APIRouter(prefix="/api/v1", tags=["repositories"])


@router.post("/repositories", response_model=Repository, status_code=status.HTTP_201_CREATED)
async def create_repository(
    payload: RepositoryCreate,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> Repository:
    """Manually register a new repository to connect and begin indexing."""
    stmt = select(db_models.Repository).where(
        db_models.Repository.owner == payload.owner,
        db_models.Repository.name == payload.name,
    )
    result = await session.execute(stmt)
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Repository already registered",
        )

    repo = db_models.Repository(
        github_installation_id=payload.github_installation_id,
        owner=payload.owner,
        name=payload.name,
        default_branch=payload.default_branch,
        index_status=IndexStatus.pending,
        posting_enabled=False,
    )
    session.add(repo)
    await session.commit()
    await session.refresh(repo)

    # Enqueue indexing job immediately
    arq_pool = request.app.state.arq_pool
    await arq_pool.enqueue_job(
        "index_repo",
        repository_id=repo.id,
        clone_url=f"https://github.com/{repo.owner}/{repo.name}.git",
        commit_sha="HEAD",
    )

    return repo.to_schema()



@router.get("/repositories", response_model=list[Repository])
async def list_repositories(session: AsyncSession = Depends(get_db_session)) -> list[Repository]:
    """List all registered repositories in the system."""
    stmt = select(db_models.Repository)
    result = await session.execute(stmt)
    repos = result.scalars().all()
    return [r.to_schema() for r in repos]


@router.get("/repositories/{id}", response_model=Repository)
async def get_repository(id: int, session: AsyncSession = Depends(get_db_session)) -> Repository:
    """Get detailed status of a specific repository."""
    stmt = select(db_models.Repository).where(db_models.Repository.id == id)
    result = await session.execute(stmt)
    repo = result.scalars().first()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )
    return repo.to_schema()


@router.patch("/repositories/{id}", response_model=Repository)
async def update_repository(
    id: int,
    payload: RepositoryUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> Repository:
    """Update settings for a repository, notably toggling comment posting."""
    stmt = select(db_models.Repository).where(db_models.Repository.id == id)
    result = await session.execute(stmt)
    repo = result.scalars().first()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )
    repo.posting_enabled = payload.posting_enabled
    await session.commit()
    return repo.to_schema()


@router.post("/repositories/{id}/reindex", status_code=status.HTTP_202_ACCEPTED)
async def reindex_repository(
    id: int,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Request a full repository re-index by enqueuing a worker job."""
    stmt = select(db_models.Repository).where(db_models.Repository.id == id)
    result = await session.execute(stmt)
    repo = result.scalars().first()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    # Use persistent arq pool from app.state
    arq_pool = request.app.state.arq_pool
    owner = repo.owner
    name = repo.name
    await arq_pool.enqueue_job(
        "index_repo",
        repository_id=repo.id,
        clone_url=f"https://github.com/{owner}/{name}.git",
        commit_sha="HEAD",
    )
    return {"status": "enqueued"}


@router.get("/repositories/{id}/conventions", response_model=list[Convention])
async def list_conventions(
    id: int,
    session: AsyncSession = Depends(get_db_session),
) -> list[Convention]:
    """List learned and user-defined coding conventions for a repository."""
    # Ensure repo exists
    repo_stmt = select(db_models.Repository).where(db_models.Repository.id == id)
    repo_result = await session.execute(repo_stmt)
    if not repo_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    stmt = select(db_models.Convention).where(db_models.Convention.repository_id == id)
    result = await session.execute(stmt)
    convs = result.scalars().all()
    return [c.to_schema() for c in convs]


@router.post(
    "/repositories/{id}/conventions",
    response_model=Convention,
    status_code=status.HTTP_201_CREATED,
)
async def create_convention(
    id: int,
    payload: ConventionCreate,
    session: AsyncSession = Depends(get_db_session),
) -> Convention:
    """Manually add a user-defined convention for the review pipeline to evaluate against."""
    repo_stmt = select(db_models.Repository).where(db_models.Repository.id == id)
    repo_result = await session.execute(repo_stmt)
    if not repo_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    conv = db_models.Convention(
        repository_id=id,
        title=payload.title,
        description=payload.description,
        example_code=payload.example_code,
        source=ConventionSource.user_defined,
        confidence=1.0,
        active=True,
    )
    session.add(conv)
    await session.commit()
    await session.refresh(conv)
    return conv.to_schema()


@router.patch("/repositories/{id}/conventions/{cid}", response_model=Convention)
async def update_convention(
    id: int,
    cid: int,
    payload: ConventionUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> Convention:
    """Enable or disable a specific codebase convention."""
    stmt = select(db_models.Convention).where(
        db_models.Convention.repository_id == id,
        db_models.Convention.id == cid,
    )
    result = await session.execute(stmt)
    conv = result.scalars().first()
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Convention not found",
        )

    conv.active = payload.active
    await session.commit()
    return conv.to_schema()
