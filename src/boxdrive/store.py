"""Abstract object store interface for S3-compatible operations."""

from abc import ABC, abstractmethod

from .schemas import (
    BucketInfo,
    BucketName,
    ContentType,
    Key,
    ListObjectsInfo,
    ListObjectsV2Info,
    MaxKeys,
    Object,
    ObjectInfo,
)


class ObjectStore(ABC):
    """Abstract base class for object store implementations."""

    @abstractmethod
    async def list_buckets(self) -> list[BucketInfo]:
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
        *,
        prefix: Key | None = None,
        delimiter: str | None = None,
        max_keys: MaxKeys = 1000,
        marker: Key | None = None,
    ) -> ListObjectsInfo:
        """List objects in a bucket."""
        pass

    @abstractmethod
    async def list_objects_v2(
        self,
        bucket_name: BucketName,
        *,
        continuation_token: Key | None = None,
        delimiter: str | None = None,
        encoding_type: str | None = None,
        max_keys: MaxKeys = 1000,
        prefix: Key | None = None,
        start_after: Key | None = None,
    ) -> ListObjectsV2Info:
        """List objects in a bucket."""
        pass

    @abstractmethod
    async def get_object(self, bucket_name: BucketName, key: Key) -> Object:
        """Get an object by bucket and key. Raises NoSuchBucket or NoSuchKey if not found."""
        pass

    @abstractmethod
    async def put_object(
        self, bucket_name: BucketName, key: Key, data: bytes, content_type: ContentType | None = None
    ) -> ObjectInfo:
        """Put an object into a bucket and return its info."""
        pass

    @abstractmethod
    async def delete_object(self, bucket_name: BucketName, key: Key) -> None:
        """Delete an object from a bucket."""
        pass

    @abstractmethod
    async def head_object(self, bucket_name: BucketName, key: Key) -> ObjectInfo:
        """Get object metadata without downloading the content. Raises NoSuchBucket or NoSuchKey if not found."""
        pass
