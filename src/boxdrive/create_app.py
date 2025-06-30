"""FastAPI application factory for S3-compatible object store API."""

import logging

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import set_tracer_provider

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

    setup_opentelemetry(app)
    return app


def setup_opentelemetry(app: FastAPI) -> None:
    resource = Resource.create(
        attributes={
            SERVICE_NAME: app.title,
            SERVICE_VERSION: app.version,
        }
    )
    trace_provider = TracerProvider(resource=resource)
    set_tracer_provider(trace_provider)

    LoggingInstrumentor().instrument(set_logging_format=True, log_level=logging.DEBUG)
    FastAPIInstrumentor.instrument_app(app)
