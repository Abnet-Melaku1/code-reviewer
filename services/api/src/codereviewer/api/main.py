from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from redis.asyncio import Redis

from codereviewer.api.config import ApiConfig
from codereviewer.api.health import router as health_router
from codereviewer.api.repositories import router as repositories_router
from codereviewer.api.reviews import router as reviews_router
from codereviewer.api.webhooks import router as webhooks_router
from codereviewer.api.websocket import router as websocket_router
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
    arq_pool = await create_pool(RedisSettings.from_dsn(config.redis_url))

    app.state.db_engine = db_engine
    app.state.redis_client = redis_client
    app.state.arq_pool = arq_pool

    yield

    # Clean up resources
    await db_engine.dispose()
    await redis_client.aclose()
    await arq_pool.close()


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

    # Register CORS Middleware to allow browser communication from frontend dev server
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Accept local requests from Vite
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(webhooks_router)
    app.include_router(repositories_router)
    app.include_router(reviews_router)
    app.include_router(websocket_router)
    return app


app = create_app()

