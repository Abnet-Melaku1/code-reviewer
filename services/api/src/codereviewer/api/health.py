from enum import StrEnum

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import text

router = APIRouter(tags=["health"])


class Liveness(StrEnum):
    ok = "ok"


class Readiness(StrEnum):
    ready = "ready"
    not_ready = "not_ready"


class HealthResponse(BaseModel):
    status: Liveness


class ReadyResponse(BaseModel):
    status: Readiness


@router.get("/healthz")
async def healthz() -> HealthResponse:
    """Liveness: the process is up. Used by the orchestrator to decide restarts."""
    return HealthResponse(status=Liveness.ok)


@router.get(
    "/readyz",
    responses={503: {"description": "Service not ready"}},
)
async def readyz(request: Request) -> ReadyResponse:
    """Readiness: check database and Redis connection status."""
    # 1. Check Database
    try:
        engine = request.app.state.db_engine
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {e}",
        ) from e

    # 2. Check Redis
    try:
        redis_client = request.app.state.redis_client
        await redis_client.ping()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Redis connection failed: {e}",
        ) from e

    return ReadyResponse(status=Readiness.ready)
