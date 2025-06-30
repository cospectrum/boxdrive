"""BoxDrive - Generic object store with S3 compatible API."""

__version__ = "0.0.1"

from .app import create_app
from .memory_store import MemoryStore
from .store import ObjectMetadata, ObjectStore

__all__ = ["create_app", "ObjectStore", "ObjectMetadata", "MemoryStore"]
