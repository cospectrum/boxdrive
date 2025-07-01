import logging
from collections.abc import AsyncIterator

from fastapi import HTTPException, Response
from fastapi.responses import StreamingResponse

from boxdrive.schemas.store import ListObjectsInfo

from . import constants, exceptions
from .schemas import BucketName, ContentType, Key, MaxKeys, xml
from .store import ObjectStore

logger = logging.getLogger(__name__)


class S3:
    def __init__(self, store: ObjectStore):
        self.store = store

    async def list_buckets(self) -> xml.ListAllMyBucketsResult:
        buckets = await self.store.list_buckets()
        buckets_xml = [
            xml.Bucket(name=bucket.name, creation_date=bucket.creation_date.isoformat()) for bucket in buckets
        ]
        owner = xml.Owner(id=constants.OWNER_ID, display_name=constants.OWNER_DISPLAY_NAME)
        buckets_model = xml.Buckets(buckets=buckets_xml)
        return xml.ListAllMyBucketsResult(owner=owner, buckets=buckets_model)

    async def list_objects_v2(
        self,
        bucket: BucketName,
        prefix: Key | None = None,
        delimiter: str | None = None,
        max_keys: MaxKeys = 1000,
        continuation_token: Key | None = None,
        start_after: Key | None = None,
    ) -> xml.ListBucketResult:
        try:
            objects_info = await self.store.list_objects_v2(
                bucket,
                prefix=prefix,
                delimiter=delimiter,
                max_keys=max_keys,
                continuation_token=continuation_token,
                start_after=start_after,
            )
            return self._build_list_bucket_result(
                bucket,
                objects_info,
                prefix=prefix,
                delimiter=delimiter,
                max_keys=max_keys,
            )
        except exceptions.NoSuchBucket:
            logger.info("Bucket %s not found", bucket)
            raise HTTPException(status_code=404, detail="The specified bucket does not exist.")

    async def list_objects(
        self,
        bucket: BucketName,
        prefix: Key | None = None,
        delimiter: str | None = None,
        max_keys: MaxKeys = 1000,
        marker: Key | None = None,
    ) -> xml.ListBucketResult:
        try:
            objects_info = await self.store.list_objects(
                bucket, prefix=prefix, delimiter=delimiter, max_keys=max_keys, marker=marker
            )
            return self._build_list_bucket_result(
                bucket,
                objects_info,
                prefix=prefix,
                delimiter=delimiter,
                max_keys=max_keys,
            )
        except exceptions.NoSuchBucket:
            logger.info("Bucket %s not found", bucket)
            raise HTTPException(status_code=404, detail="The specified bucket does not exist.")

    def _build_list_bucket_result(
        self,
        bucket: BucketName,
        objects_info: ListObjectsInfo,
        prefix: Key | None = None,
        delimiter: str | None = None,
        max_keys: MaxKeys = 1000,
    ) -> xml.ListBucketResult:
        objects: list[xml.Content] = []
        for obj in objects_info.objects:
            etag = f'"{obj.etag}"' if obj.etag else ""
            objects.append(
                xml.Content(
                    key=obj.key,
                    last_modified=obj.last_modified.isoformat(),
                    etag=etag,
                    size=obj.size,
                    storage_class=constants.DEFAULT_STORAGE_CLASS,
                    owner=xml.Owner(id=constants.OWNER_ID, display_name=constants.OWNER_DISPLAY_NAME),
                )
            )
        return xml.ListBucketResult(
            name=bucket,
            prefix=prefix or "",
            max_keys=max_keys,
            key_count=len(objects) + len(objects_info.common_prefixes),
            is_truncated=objects_info.is_truncated,
            delimiter=delimiter,
            contents=objects,
            common_prefixes=[xml.CommonPrefix(prefix=prefix) for prefix in objects_info.common_prefixes],
        )

    async def get_object(
        self,
        bucket: BucketName,
        key: Key,
        range_header: str | None = None,
    ) -> StreamingResponse:
        obj = await self.store.get_object(bucket, key)
        if obj is None:
            raise HTTPException(status_code=404, detail="Object not found")
        data = obj.data
        metadata = obj.info
        start = 0
        end = len(data) - 1
        original_size = len(data)
        status_code = 200
        content_range = None
        if range_header:
            try:
                range_str = range_header.replace("bytes=", "")
                if "-" in range_str:
                    start_str, end_str = range_str.split("-", 1)
                    start = int(start_str) if start_str else 0
                    end = int(end_str) if end_str else len(data) - 1
                    if start > end or start >= len(data):
                        raise ValueError
                    data = data[start : end + 1]
                    content_range = f"bytes {start}-{end}/{original_size}"
                    status_code = 206
            except (ValueError, IndexError):
                raise HTTPException(status_code=416, detail="Requested Range Not Satisfiable")

        async def generate() -> AsyncIterator[bytes]:
            yield data

        headers: dict[str, str] = {
            "Content-Length": str(len(data)),
            "ETag": f'"{metadata.etag}"',
            "Last-Modified": metadata.last_modified.strftime("%a, %d %b %Y %H:%M:%S GMT"),
            "Content-Type": metadata.content_type,
            "Accept-Ranges": "bytes",
        }
        if content_range:
            headers["Content-Range"] = content_range
        return StreamingResponse(
            generate(),
            media_type=metadata.content_type,
            headers=headers,
            status_code=status_code,
        )

    async def head_object(self, bucket: BucketName, key: Key) -> Response:
        metadata = await self.store.head_object(bucket, key)
        if not metadata:
            raise HTTPException(status_code=404, detail="Object not found")
        return Response(
            status_code=200,
            headers={
                "Content-Length": str(metadata.size),
                "ETag": f'"{metadata.etag}"',
                "Last-Modified": metadata.last_modified.strftime("%a, %d %b %Y %H:%M:%S GMT"),
                "Content-Type": metadata.content_type,
                "Accept-Ranges": "bytes",
            },
        )

    async def put_object(
        self,
        bucket: BucketName,
        key: Key,
        content: bytes,
        content_type: ContentType | None = None,
    ) -> Response:
        final_content_type = content_type or constants.DEFAULT_CONTENT_TYPE
        result_etag = await self.store.put_object(bucket, key, content, final_content_type)
        return Response(status_code=200, headers={"ETag": f'"{result_etag}"', "Content-Length": "0"})

    async def delete_object(self, bucket: BucketName, key: Key) -> None:
        try:
            await self.store.delete_object(bucket, key)
        except exceptions.NoSuchBucket:
            logger.info("Bucket %s not found", bucket)
        except exceptions.NoSuchKey:
            logger.info("Object %s not found in bucket %s", key, bucket)
        return None

    async def create_bucket(self, bucket: BucketName) -> Response:
        try:
            await self.store.create_bucket(bucket)
        except exceptions.BucketAlreadyExists:
            raise HTTPException(status_code=409, detail="Bucket already exists")
        return Response(status_code=200, headers={"Location": f"/{bucket}"})

    async def delete_bucket(self, bucket: BucketName) -> Response:
        try:
            await self.store.delete_bucket(bucket)
        except exceptions.NoSuchBucket:
            logger.info("Bucket %s not found", bucket)
        return Response(status_code=204)
