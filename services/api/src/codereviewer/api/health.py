from enum import StrEnum

from fastapi import APIRouter
from pydantic import BaseModel

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


@router.get("/readyz")
async def readyz() -> ReadyResponse:
    """Readiness: the service can serve traffic.

    Trivially ready for now; it will check dependencies (database, Redis) once they are
    wired, and report ``not_ready`` so the orchestrator holds traffic until they are up.
    """
    return ReadyResponse(status=Readiness.ready)
