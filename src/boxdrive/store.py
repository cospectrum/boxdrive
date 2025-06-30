"""Abstract object store interface for S3-compatible operations."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import datetime


class ObjectMetadata:
    """Metadata for an object in the store."""

    def __init__(
        self,
        key: str,
        size: int,
        last_modified: datetime,
        etag: str | None = None,
        content_type: str | None = None,
    ):
        self.key = key
        self.size = size
        self.last_modified = last_modified
        self.etag = etag
        self.content_type = content_type


class ObjectStore(ABC):
    """Abstract base class for object store implementations."""

    @abstractmethod
    async def list_objects(
        self, prefix: str | None = None, delimiter: str | None = None, max_keys: int | None = None
    ) -> AsyncIterator[ObjectMetadata]:
        """List objects in the store."""
        raise NotImplementedError
        yield ObjectMetadata(key="", size=0, last_modified=datetime.now())

    @abstractmethod
    async def get_object(self, key: str) -> bytes | None:
        """Get an object by key."""
        pass

    @abstractmethod
    async def put_object(self, key: str, data: bytes, content_type: str | None = None) -> str:
        """Put an object into the store."""
        pass

    @abstractmethod
    async def delete_object(self, key: str) -> bool:
        """Delete an object from the store."""
        pass

    @abstractmethod
    async def head_object(self, key: str) -> ObjectMetadata | None:
        """Get object metadata without downloading the content."""
        pass

    @abstractmethod
    async def object_exists(self, key: str) -> bool:
        """Check if an object exists."""
        pass

    @abstractmethod
    async def get_object_stream(self, key: str) -> AsyncIterator[bytes] | None:
        """Get an object as a stream."""
        pass

    @abstractmethod
    async def put_object_stream(self, key: str, stream: AsyncIterator[bytes], content_type: str | None = None) -> str:
        """Put an object from a stream."""
        pass
