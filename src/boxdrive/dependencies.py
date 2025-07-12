from fastapi import Header, Request

from .s3 import S3
from .store import ObjectStore

TraceParentHeader = Header(
    pattern="^00-[0-9a-f]{32}-[0-9a-f]{16}-0[0-9a-f]$",
    description="""
    {version}-{trace-id}-{parent-id}-{trace-flags}

    spec: https://www.w3.org/TR/trace-context/
    """,
    examples=["00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"],
    default_factory=lambda: f"00-{'0' * 32}-{'0' * 16}-00",
)


def opentelemetry_headers(
    traceparent: str = TraceParentHeader,
) -> None:
    _ = traceparent


def get_store(request: Request) -> ObjectStore:
    store: ObjectStore = request.app.state.store
    return store


def get_s3(request: Request) -> S3:
    return S3(get_store(request))
