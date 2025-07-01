"""In-memory implementation of ObjectStore for testing and development."""

import datetime
import hashlib
import logging

from pydantic import BaseModel

from boxdrive import exceptions
from boxdrive.schemas.store import ListObjectsV2Info

from .. import constants
from ..schemas import (
    BucketInfo,
    BucketName,
    ContentType,
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

    @staticmethod
    def _split_contents_and_prefixes(
        objects: list[ObjectInfo], *, prefix: Key | None, delimiter: str | None
    ) -> tuple[list[ObjectInfo], list[str]]:
        prefix = prefix or ""
        if not delimiter:
            return objects, []
        contents = []
        common_prefixes = set()
        plen = len(prefix)
        for obj in objects:
            assert obj.key.startswith(prefix), "all objects must be filtered by prefix before splitting"
            key = obj.key[plen:]
            if delimiter in key:
                idx = key.index(delimiter)
                common_prefix = obj.key[: plen + idx + len(delimiter)]
                common_prefixes.add(common_prefix)
            else:
                contents.append(obj)
        return contents, sorted(common_prefixes)

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

        objects, common_prefixes = self._split_contents_and_prefixes(objects, prefix=prefix, delimiter=delimiter)

        is_truncated = len(objects) > max_keys
        objects = objects[:max_keys]

        return ListObjectsInfo(objects=objects, is_truncated=is_truncated, common_prefixes=common_prefixes)

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

        objects, common_prefixes = self._split_contents_and_prefixes(objects, prefix=prefix, delimiter=delimiter)

        is_truncated = len(objects) > max_keys
        objects = objects[:max_keys]

        return ListObjectsV2Info(objects=objects, is_truncated=is_truncated, common_prefixes=common_prefixes)

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

        etag = hashlib.md5(data).hexdigest()
        now = datetime.datetime.now(datetime.UTC)
        final_content_type = content_type or constants.DEFAULT_CONTENT_TYPE
        info = ObjectInfo(key=key, size=len(data), last_modified=now, etag=etag, content_type=final_content_type)
        obj = Object(data=data, info=info)

        bucket = self.buckets.get(bucket_name)
        if bucket is None:
            return info
        bucket.objects[key] = obj
        return info

    async def delete_object(self, bucket_name: str, key: Key) -> ObjectInfo:
        """Delete an object from a bucket."""
        bucket = self.buckets.get(bucket_name)
        if bucket is None:
            raise exceptions.NoSuchBucket
        try:
            return bucket.objects.pop(key).info
        except KeyError:
            raise exceptions.NoSuchKey

    async def head_object(self, bucket_name: str, key: Key) -> ObjectInfo:
        bucket = self.buckets.get(bucket_name)
        if bucket is None:
            raise exceptions.NoSuchBucket
        obj = bucket.objects.get(key)
        if obj is None:
            raise exceptions.NoSuchKey
        return obj.info
