"""In-memory implementation of ObjectStore for testing and development."""

import datetime
import hashlib
import logging

from pydantic import BaseModel

from boxdrive import exceptions

from .. import constants
from ..schemas import (
    BucketInfo,
    BucketName,
    ContentType,
    ETag,
    Key,
    ListObjectsInfo,
    MaxKeys,
    Object,
    ObjectInfo,
)
from ..store import ObjectStore

logger = logging.getLogger(__name__)


class Bucket(BaseModel):
    """Represents a bucket with its objects and info."""

    info: BucketInfo
    objects: dict[Key, "Object"]


Buckets = dict[BucketName, Bucket]


class InMemoryStore(ObjectStore):
    """In-memory object store implementation."""

    def __init__(self, *, buckets: Buckets | None = None) -> None:
        self.buckets = buckets or {}

    async def list_buckets(self) -> list[BucketInfo]:
        """List all buckets in the store."""
        return [bucket.info for bucket in self.buckets.values()]

    async def create_bucket(self, bucket_name: BucketName) -> None:
        """Create a new bucket in the store."""
        bucket = Bucket(
            objects={},
            info=BucketInfo(
                name=bucket_name,
                creation_date=datetime.datetime.now(datetime.UTC),
            ),
        )
        in_store_bucket = self.buckets.setdefault(bucket_name, bucket)
        if in_store_bucket != bucket:
            raise exceptions.BucketAlreadyExists

    async def delete_bucket(self, bucket_name: BucketName) -> None:
        try:
            del self.buckets[bucket_name]
        except KeyError:
            raise exceptions.NoSuchBucket

    async def list_objects(
        self,
        bucket_name: str,
        *,
        prefix: Key | None = None,
        delimiter: str | None = None,
        max_keys: MaxKeys = 1000,
        marker: Key | None = None,
    ) -> ListObjectsInfo:
        bucket = self.buckets.get(bucket_name)
        if bucket is None:
            raise exceptions.NoSuchBucket

        objects = [obj.info for obj in bucket.objects.values()]
        if prefix:
            objects = [obj for obj in objects if obj.key.startswith(prefix)]

        objects = sorted(objects, key=lambda obj: obj.key)
        if marker:
            objects = [obj for obj in objects if obj.key > marker]

        is_truncated = len(objects) > max_keys
        objects = objects[:max_keys]

        return ListObjectsInfo(objects=objects, is_truncated=is_truncated)

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
    ) -> ListObjectsInfo:
        bucket = self.buckets.get(bucket_name)
        if bucket is None:
            raise exceptions.NoSuchBucket

        objects = [obj.info for obj in bucket.objects.values()]
        if prefix:
            objects = [obj for obj in objects if obj.key.startswith(prefix)]
        objects = sorted(objects, key=lambda obj: obj.key)

        after = continuation_token or start_after
        if after:
            objects = [obj for obj in objects if obj.key > after]

        is_truncated = len(objects) > max_keys
        objects = objects[:max_keys]

        return ListObjectsInfo(objects=objects, is_truncated=is_truncated)

    async def get_object(self, bucket_name: str, key: Key) -> Object | None:
        """Get an object by bucket and key."""
        bucket = self.buckets.get(bucket_name)
        if bucket is None:
            return None
        return bucket.objects.get(key)

    async def put_object(
        self, bucket_name: str, key: Key, data: bytes, content_type: ContentType | None = None
    ) -> ETag:
        """Put an object into a bucket."""
        if bucket_name not in self.buckets:
            await self.create_bucket(bucket_name)

        etag = hashlib.md5(data).hexdigest()
        now = datetime.datetime.now(datetime.UTC)
        final_content_type = content_type or constants.DEFAULT_CONTENT_TYPE
        info = ObjectInfo(key=key, size=len(data), last_modified=now, etag=etag, content_type=final_content_type)
        obj = Object(data=data, info=info)

        bucket = self.buckets.get(bucket_name)
        if bucket is None:
            return etag
        bucket.objects[key] = obj
        return etag

    async def delete_object(self, bucket_name: str, key: Key) -> None:
        """Delete an object from a bucket."""
        bucket = self.buckets.get(bucket_name)
        if bucket is None:
            raise exceptions.NoSuchBucket
        try:
            del bucket.objects[key]
        except KeyError:
            raise exceptions.NoSuchKey

    async def head_object(self, bucket_name: str, key: Key) -> ObjectInfo | None:
        """Get object info without downloading the content."""
        bucket = self.buckets.get(bucket_name)
        if bucket is None:
            return None
        try:
            return bucket.objects[key].info
        except KeyError:
            return None
