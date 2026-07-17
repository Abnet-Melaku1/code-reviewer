from fastapi import FastAPI

from codereviewer.api.health import router as health_router


def create_app() -> FastAPI:
    """Build the FastAPI application.

    A factory (not a module-level singleton alone) so tests and future entrypoints can
    construct isolated app instances; ``app`` below is the default instance for the ASGI
    server and the OpenAPI type-generation pipeline.
    """
    app = FastAPI(title="CodeReviewer.ai API", version="0.0.0")
    app.include_router(health_router)
    return app


app = create_app()
