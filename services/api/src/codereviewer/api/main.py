from fastapi import FastAPI
from fastapi.routing import APIRoute

from codereviewer.api.health import router as health_router


def _operation_id(route: APIRoute) -> str:
    """Stable, readable operation ids (``tag_name``) so generated TS names don't churn.

    FastAPI's default (``<name>_<name>_<method>``) produces ugly, path-derived identifiers;
    tag-scoping keeps them unique across routers.
    """
    tag = str(route.tags[0]) if route.tags else "default"
    return f"{tag}_{route.name}"


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
    )
    app.include_router(health_router)
    return app


app = create_app()
