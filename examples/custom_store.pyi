import datetime
from collections.abc import AsyncIterator

from boxdrive import (
    BucketMetadata,
    ContentType,
    ETag,
    MaxKeys,
    Object,
    ObjectMetadata,
    ObjectStore,
)

class MyCustomStore(ObjectStore):
    async def list_buckets(self) -> list[BucketMetadata]: ...
    async def create_bucket(self, bucket_name: str) -> None: ...
    async def delete_bucket(self, bucket_name: str) -> None: ...  # raises NoSuchBucket
    async def list_objects(
        self, bucket_name: str, prefix: str | None = None, delimiter: str | None = None, max_keys: MaxKeys | None = None
    ) -> AsyncIterator[ObjectMetadata]:
        yield ObjectMetadata(
            key="", size=0, last_modified=datetime.datetime.now(datetime.UTC), etag="", content_type=""
        )
    async def get_object(self, bucket_name: str, key: str) -> Object | None: ...
    async def put_object(
        self, bucket_name: str, key: str, data: bytes, content_type: ContentType | None = None
    ) -> ETag: ...
    async def delete_object(self, bucket_name: str, key: str) -> None: ...  # raises NoSuchKey
    async def head_object(self, bucket_name: str, key: str) -> ObjectMetadata | None: ...
