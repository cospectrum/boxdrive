"""FastAPI application factory for S3-compatible object store API."""

from fastapi import FastAPI

from .handlers import router
from .store import ObjectStore


def create_app(store: ObjectStore) -> FastAPI:
    """Create a FastAPI application with S3-compatible endpoints.

    Args:
        store: The object store implementation to use

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(title="BoxDrive", description="S3-compatible object store API", version="0.0.1")
    app.state.store = store
    app.include_router(router)
    return app
