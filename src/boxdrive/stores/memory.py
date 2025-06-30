"""In-memory implementation of ObjectStore for testing and development."""

import datetime
import hashlib
from collections.abc import AsyncIterator

from pydantic import BaseModel

from .. import constants
from ..schemas import BucketMetadata, BucketName, ContentType, ETag, Key, MaxKeys, Object, ObjectMetadata
from ..store import ObjectStore


class Bucket(BaseModel):
    """Represents a bucket with its objects and creation date."""

    name: BucketName
    creation_date: datetime.datetime
    objects: dict[Key, "Object"]


class MemoryStore(ObjectStore):
    """In-memory object store implementation."""

    def __init__(self) -> None:
        self._buckets: dict[BucketName, Bucket] = {}

    async def list_buckets(self) -> list[BucketMetadata]:
        """List all buckets in the store."""
        buckets = []
        for bucket in self._buckets.values():
            buckets.append(BucketMetadata(name=bucket.name, creation_date=bucket.creation_date))
        return buckets

    async def create_bucket(self, bucket_name: BucketName) -> bool:
        """Create a new bucket in the store."""
        if bucket_name in self._buckets:
            return False
        self._buckets[bucket_name] = Bucket(
            name=bucket_name, creation_date=datetime.datetime.now(datetime.UTC), objects={}
        )
        return True

    async def delete_bucket(self, bucket_name: BucketName) -> bool:
        if bucket_name in self._buckets:
            del self._buckets[bucket_name]
            return True
        return False

    async def list_objects(
        self, bucket_name: str, prefix: Key | None = None, delimiter: str | None = None, max_keys: MaxKeys | None = None
    ) -> AsyncIterator[ObjectMetadata]:
        if bucket_name not in self._buckets:
            return

        bucket = self._buckets[bucket_name]
        keys = list(bucket.objects.keys())

        if prefix:
            keys = [k for k in keys if k.startswith(prefix)]

        if max_keys:
            keys = keys[:max_keys]

        for key in keys:
            yield bucket.objects[key].metadata

    async def get_object(self, bucket_name: str, key: Key) -> Object | None:
        """Get an object by bucket and key."""
        if bucket_name not in self._buckets:
            return None
        bucket = self._buckets[bucket_name]
        return bucket.objects.get(key)

    async def put_object(
        self, bucket_name: str, key: Key, data: bytes, content_type: ContentType | None = None
    ) -> ETag:
        """Put an object into a bucket."""
        if bucket_name not in self._buckets:
            await self.create_bucket(bucket_name)

        bucket = self._buckets[bucket_name]
        now = datetime.datetime.now(datetime.UTC)
        etag = hashlib.md5(data).hexdigest()
        final_content_type = content_type or constants.DEFAULT_CONTENT_TYPE
        metadata = ObjectMetadata(
            key=key, size=len(data), last_modified=now, etag=etag, content_type=final_content_type
        )

        bucket.objects[key] = Object(data=data, metadata=metadata)
        return etag

    async def delete_object(self, bucket_name: str, key: Key) -> bool:
        """Delete an object from a bucket."""
        if bucket_name not in self._buckets:
            return False
        bucket = self._buckets[bucket_name]
        if key in bucket.objects:
            del bucket.objects[key]
            return True
        return False

    async def head_object(self, bucket_name: str, key: Key) -> ObjectMetadata | None:
        """Get object metadata without downloading the content."""
        if bucket_name not in self._buckets:
            return None
        bucket = self._buckets[bucket_name]
        if key in bucket.objects:
            return bucket.objects[key].metadata
        return None
