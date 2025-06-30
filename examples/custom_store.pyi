from boxdrive import (
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
    ObjectStore,
)

class MyCustomStore(ObjectStore):
    async def list_buckets(self) -> list[BucketInfo]: ...
    async def create_bucket(self, bucket_name: BucketName) -> None: ...
    async def delete_bucket(self, bucket_name: BucketName) -> None: ...
    async def get_object(self, bucket_name: BucketName, key: Key) -> Object | None: ...
    async def put_object(
        self, bucket_name: BucketName, key: Key, data: bytes, content_type: ContentType | None = None
    ) -> ETag: ...
    async def delete_object(self, bucket_name: BucketName, key: Key) -> None: ...
    async def head_object(self, bucket_name: BucketName, key: Key) -> ObjectInfo | None: ...
    async def list_objects(
        self,
        bucket_name: BucketName,
        *,
        prefix: Key | None = None,
        delimiter: str | None = None,
        max_keys: MaxKeys = 1000,
        marker: Key | None = None,
    ) -> ListObjectsInfo: ...
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
    ) -> ListObjectsV2Info: ...
