"""FastAPI application factory for S3-compatible object store API."""

from fastapi import FastAPI

from .handlers import router
from .middleware import ExceptionHandlerMiddleware, RequestLoggingMiddleware
from .store import ObjectStore
from .version import __version__


def create_app(store: ObjectStore) -> FastAPI:
    """Create a FastAPI application with S3-compatible endpoints.

    Args:
        store: The object store implementation to use

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(title="BoxDrive", description="S3-compatible object store API", version=__version__)
    app.state.store = store

    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(ExceptionHandlerMiddleware)

    app.include_router(router)
    return app
