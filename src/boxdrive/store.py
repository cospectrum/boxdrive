"""Abstract object store interface for S3-compatible operations."""

import datetime
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from .schemas import (
    BucketMetadata,
    BucketName,
    ContentType,
    ETag,
    Key,
    MaxKeys,
    ObjectMetadata,
)


class ObjectStore(ABC):
    """Abstract base class for object store implementations."""

    @abstractmethod
    async def list_buckets(self) -> list[BucketMetadata]:
        """List all buckets in the store."""
        pass

    @abstractmethod
    async def create_bucket(self, bucket_name: BucketName) -> bool:
        """Create a new bucket in the store."""
        pass

    @abstractmethod
    async def list_objects(
        self, prefix: Key | None = None, delimiter: str | None = None, max_keys: MaxKeys | None = None
    ) -> AsyncIterator[ObjectMetadata]:
        """List objects in the store."""
        raise NotImplementedError
        yield ObjectMetadata(key="", size=0, last_modified=datetime.datetime.now())

    @abstractmethod
    async def get_object(self, key: Key) -> bytes | None:
        """Get an object by key."""
        pass

    @abstractmethod
    async def put_object(self, key: Key, data: bytes, content_type: ContentType | None = None) -> ETag:
        """Put an object into the store."""
        pass

    @abstractmethod
    async def delete_object(self, key: Key) -> bool:
        """Delete an object from the store."""
        pass

    @abstractmethod
    async def head_object(self, key: Key) -> ObjectMetadata | None:
        """Get object metadata without downloading the content."""
        pass

    @abstractmethod
    async def object_exists(self, key: Key) -> bool:
        """Check if an object exists."""
        pass

    @abstractmethod
    async def get_object_stream(self, key: Key) -> AsyncIterator[bytes] | None:
        """Get an object as a stream."""
        pass

    @abstractmethod
    async def put_object_stream(
        self, key: Key, stream: AsyncIterator[bytes], content_type: ContentType | None = None
    ) -> ETag:
        """Put an object from a stream."""
        pass
