"""Middleware for BoxDrive S3-compatible API."""

import logging
import time
from typing import Any

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from opentelemetry.propagate import inject
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from .exceptions import BucketAlreadyExists, NoSuchBucket, NoSuchKey

logger = logging.getLogger(__name__)


class LogInfo(BaseHTTPMiddleware):
    """Middleware to log request and response information."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        method = request.method
        path = request.url.path
        query_params = request.url.query
        logger.info(
            "Request info: %s",
            {
                "method": method,
                "path": path,
                "query_params": query_params,
                "client_host": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            },
        )

        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        status_code = response.status_code
        content_length = response.headers.get("content-length", "unknown")
        logger.info(
            "Response info: %s",
            {
                "method": method,
                "path": path,
                "status_code": status_code,
                "process_time": f"{process_time:.3f}s",
                "content_length": content_length,
            },
        )
        return response


class Recover(BaseHTTPMiddleware):
    """Middleware to handle exceptions globally and provide consistent error responses."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            response = await call_next(request)
            return response
        except NoSuchBucket:
            return JSONResponse(
                status_code=404, content={"error": "NoSuchBucket", "message": "The specified bucket does not exist."}
            )
        except NoSuchKey:
            return JSONResponse(
                status_code=404, content={"error": "NoSuchKey", "message": "The specified key does not exist."}
            )
        except BucketAlreadyExists:
            return JSONResponse(
                status_code=409, content={"error": "BucketAlreadyExists", "message": "Bucket already exists."}
            )
        except Exception as exc:
            logger.exception("internal error")
            detail = f"Internal Server Error {type(exc)}"
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred",
                    "detail": detail,
                },
            )


class InjectOtelContextIntoResponse(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        carrier: dict[Any, Any] = {}
        inject(carrier)
        for key, value in carrier.items():
            response.headers.append(key, value)
        return response
