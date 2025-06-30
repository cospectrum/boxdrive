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
    Object,
    ObjectMetadata,
)


class ObjectStore(ABC):
    """Abstract base class for object store implementations."""

    @abstractmethod
    async def list_buckets(self) -> list[BucketMetadata]:
        """List all buckets in the store."""
        pass

    @abstractmethod
    async def create_bucket(self, bucket_name: BucketName) -> None:
        """Create a new bucket in the store."""
        pass

    @abstractmethod
    async def delete_bucket(self, bucket_name: BucketName) -> None:
        """Delete a bucket from the store."""
        pass

    @abstractmethod
    async def list_objects(
        self,
        bucket_name: BucketName,
        prefix: Key | None = None,
        delimiter: str | None = None,
        max_keys: MaxKeys | None = None,
    ) -> AsyncIterator[ObjectMetadata]:
        """List objects in a bucket."""
        raise NotImplementedError
        yield ObjectMetadata(
            key="", size=0, last_modified=datetime.datetime.now(datetime.UTC), etag="", content_type=""
        )

    @abstractmethod
    async def get_object(self, bucket_name: BucketName, key: Key) -> Object | None:
        """Get an object by bucket and key."""
        pass

    @abstractmethod
    async def put_object(
        self, bucket_name: BucketName, key: Key, data: bytes, content_type: ContentType | None = None
    ) -> ETag:
        """Put an object into a bucket."""
        pass

    @abstractmethod
    async def delete_object(self, bucket_name: BucketName, key: Key) -> None:
        """Delete an object from a bucket."""
        pass

    @abstractmethod
    async def head_object(self, bucket_name: BucketName, key: Key) -> ObjectMetadata | None:
        """Get object metadata without downloading the content."""
        pass
