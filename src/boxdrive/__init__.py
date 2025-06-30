"""BoxDrive - Generic object store with S3 compatible API."""

from . import stores
from .create_app import create_app
from .schemas import BucketName, ContentType, ETag, Key, MaxKeys, ObjectMetadata
from .store import ObjectStore
from .version import __version__

__all__ = [
    "__version__",
    "stores",
    "create_app",
    "ObjectStore",
    "ObjectMetadata",
    "BucketName",
    "ContentType",
    "ETag",
    "Key",
    "MaxKeys",
]
