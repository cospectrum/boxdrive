"""BoxDrive - Generic object store with S3 compatible API."""

from . import exceptions, stores
from .create_app import create_app
from .schemas import (
    BucketMetadata,
    BucketName,
    ContentType,
    ETag,
    Key,
    ListObjectsInfo,
    MaxKeys,
    Object,
    ObjectMetadata,
)
from .store import ObjectStore
from .version import __version__

__all__ = [
    "__version__",
    "exceptions",
    "stores",
    "create_app",
    "ObjectStore",
    "ObjectMetadata",
    "BucketMetadata",
    "Object",
    "ListObjectsInfo",
    "BucketName",
    "ContentType",
    "ETag",
    "Key",
    "MaxKeys",
]
