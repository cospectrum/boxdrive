from boxdrive import (
    BucketMetadata,
    ContentType,
    ETag,
    ListObjectsInfo,
    MaxKeys,
    Object,
    ObjectMetadata,
    ObjectStore,
)

class MyCustomStore(ObjectStore):
    async def list_buckets(self) -> list[BucketMetadata]: ...
    async def create_bucket(self, bucket_name: str) -> None: ...
    async def delete_bucket(self, bucket_name: str) -> None: ...
    async def list_objects(
        self,
        bucket_name: str,
        *,
        prefix: str | None = None,
        delimiter: str | None = None,
        max_keys: MaxKeys = 1000,
        marker: str | None = None,
    ) -> ListObjectsInfo: ...
    async def get_object(self, bucket_name: str, key: str) -> Object | None: ...
    async def put_object(
        self, bucket_name: str, key: str, data: bytes, content_type: ContentType | None = None
    ) -> ETag: ...
    async def delete_object(self, bucket_name: str, key: str) -> None: ...
    async def head_object(self, bucket_name: str, key: str) -> ObjectMetadata | None: ...
