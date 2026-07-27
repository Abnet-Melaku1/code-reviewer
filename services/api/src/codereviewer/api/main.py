from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.routing import APIRoute
from redis.asyncio import Redis

from codereviewer.api.config import ApiConfig
from codereviewer.api.health import router as health_router
from codereviewer.api.webhooks import router as webhooks_router
from codereviewer.db.session import make_engine


def _operation_id(route: APIRoute) -> str:
    """Stable, readable operation ids (``tag_name``) so generated TS names don't churn.

    FastAPI's default (``<name>_<name>_<method>``) produces ugly, path-derived identifiers;
    tag-scoping keeps them unique across routers.
    """
    tag = str(route.tags[0]) if route.tags else "default"
    return f"{tag}_{route.name}"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage lifecycle of persistent database and Redis connection resources."""
    config = ApiConfig()

    # Create engine & Redis client
    db_engine = make_engine(config.database_url)
    redis_client = Redis.from_url(config.redis_url, decode_responses=True)

    app.state.db_engine = db_engine
    app.state.redis_client = redis_client

    yield

    # Clean up resources
    await db_engine.dispose()
    await redis_client.aclose()


def create_app() -> FastAPI:
    """Build the FastAPI application.

    A factory (not a module-level singleton alone) so tests and future entrypoints can
    construct isolated app instances; ``app`` below is the default instance for the ASGI
    server and the OpenAPI type-generation pipeline.
    """
    app = FastAPI(
        title="CodeReviewer.ai API",
        version="0.0.0",
        generate_unique_id_function=_operation_id,
        lifespan=lifespan,
    )
    app.include_router(health_router)
    app.include_router(webhooks_router)
    return app


app = create_app()
