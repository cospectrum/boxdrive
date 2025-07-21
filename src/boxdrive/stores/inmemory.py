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
    ListObjectsV2Info,
    MaxKeys,
    Object,
    ObjectInfo,
)
from ..store import ObjectStore
from ._utils import filter_objects, filter_objects_v2


def get_etag(data: bytes) -> ETag:
    return hashlib.md5(data).hexdigest()


logger = logging.getLogger(__name__)


class Bucket(BaseModel):
    """Represents a bucket with its objects and info."""

    info: BucketInfo
    objects: dict[Key, "Object"]


Buckets = dict[BucketName, Bucket]


class InMemoryStore(ObjectStore):
    """In-memory object store implementation.

    Note: The store can raise unexpected RuntimeError in multi-threaded code.
    """

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
        prefix: str | None = None,
        delimiter: str | None = None,
        max_keys: MaxKeys = constants.MAX_KEYS,
        marker: Key | None = None,
        encoding_type: str | None = None,
    ) -> ListObjectsInfo:
        bucket = self.buckets.get(bucket_name)
        if bucket is None:
            raise exceptions.NoSuchBucket
        objects = [obj.info for obj in bucket.objects.values()]
        return filter_objects(
            objects, prefix=prefix, delimiter=delimiter, max_keys=max_keys, marker=marker, encoding_type=encoding_type
        )

    async def list_objects_v2(
        self,
        bucket_name: BucketName,
        *,
        continuation_token: Key | None = None,
        delimiter: str | None = None,
        encoding_type: str | None = None,
        max_keys: MaxKeys = constants.MAX_KEYS,
        prefix: str | None = None,
        start_after: Key | None = None,
    ) -> ListObjectsV2Info:
        bucket = self.buckets.get(bucket_name)
        if bucket is None:
            raise exceptions.NoSuchBucket
        objects = [obj.info for obj in bucket.objects.values()]
        return filter_objects_v2(
            objects,
            continuation_token=continuation_token,
            delimiter=delimiter,
            encoding_type=encoding_type,
            max_keys=max_keys,
            prefix=prefix,
            start_after=start_after,
        )

    async def get_object(self, bucket_name: str, key: Key) -> Object:
        bucket = self.buckets.get(bucket_name)
        if bucket is None:
            raise exceptions.NoSuchBucket
        obj = bucket.objects.get(key)
        if obj is None:
            raise exceptions.NoSuchKey
        return obj

    async def put_object(
        self, bucket_name: str, key: Key, data: bytes, content_type: ContentType | None = None
    ) -> ObjectInfo:
        """Put an object into a bucket."""
        if bucket_name not in self.buckets:
            await self.create_bucket(bucket_name)

        etag = get_etag(data)
        now = datetime.datetime.now(datetime.UTC)
        final_content_type = content_type or constants.DEFAULT_CONTENT_TYPE
        info = ObjectInfo(key=key, size=len(data), last_modified=now, etag=etag, content_type=final_content_type)
        obj = Object(data=data, info=info)

        bucket = self.buckets.get(bucket_name)
        if bucket is None:
            return info
        bucket.objects[key] = obj
        return info

    async def delete_object(self, bucket_name: str, key: Key) -> None:
        """Delete an object from a bucket."""
        bucket = self.buckets.get(bucket_name)
        if bucket is None:
            raise exceptions.NoSuchBucket
        try:
            del bucket.objects[key]
        except KeyError:
            pass

    async def head_object(self, bucket_name: str, key: Key) -> ObjectInfo:
        bucket = self.buckets.get(bucket_name)
        if bucket is None:
            raise exceptions.NoSuchBucket
        obj = bucket.objects.get(key)
        if obj is None:
            raise exceptions.NoSuchKey
        return obj.info
