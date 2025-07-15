import logging
import os
from collections.abc import AsyncIterator

from fastapi import HTTPException, Response, status
from fastapi.responses import StreamingResponse
from opentelemetry import trace

from boxdrive.schemas import BaseListObjectsInfo

from . import constants, exceptions
from .schemas import BucketName, ContentType, Key, MaxKeys, xml
from .store import ObjectStore

tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)


class S3:
    def __init__(self, store: ObjectStore):
        self.store = store

    @tracer.start_as_current_span("list_buckets")
    async def list_buckets(self) -> xml.ListAllMyBucketsResult:
        buckets = await self.store.list_buckets()
        buckets_xml = [
            xml.Bucket(name=bucket.name, creation_date=bucket.creation_date.isoformat()) for bucket in buckets
        ]
        owner = xml.Owner(id=constants.OWNER_ID, display_name=constants.OWNER_DISPLAY_NAME)
        buckets_model = xml.Buckets(buckets=buckets_xml)
        return xml.ListAllMyBucketsResult(owner=owner, buckets=buckets_model)

    @tracer.start_as_current_span("list_objects_v2")
    async def list_objects_v2(
        self,
        bucket: BucketName,
        prefix: Key | None = None,
        delimiter: str | None = None,
        max_keys: MaxKeys = constants.MAX_KEYS,
        continuation_token: Key | None = None,
        start_after: Key | None = None,
        encoding_type: str | None = None,
    ) -> xml.ListBucketResult:
        objects_info = await self.store.list_objects_v2(
            bucket,
            prefix=prefix,
            delimiter=delimiter,
            max_keys=max_keys,
            continuation_token=continuation_token,
            start_after=start_after,
            encoding_type=encoding_type,
        )
        return self._build_list_bucket_result(
            bucket,
            objects_info,
            prefix=prefix,
            delimiter=delimiter,
            max_keys=max_keys,
        )

    @tracer.start_as_current_span("list_objects")
    async def list_objects(
        self,
        bucket: BucketName,
        prefix: Key | None = None,
        delimiter: str | None = None,
        max_keys: MaxKeys = constants.MAX_KEYS,
        marker: Key | None = None,
        encoding_type: str | None = None,
    ) -> xml.ListBucketResult:
        objects_info = await self.store.list_objects(
            bucket, prefix=prefix, delimiter=delimiter, max_keys=max_keys, marker=marker, encoding_type=encoding_type
        )
        return self._build_list_bucket_result(
            bucket,
            objects_info,
            prefix=prefix,
            delimiter=delimiter,
            max_keys=max_keys,
        )

    def _build_list_bucket_result(
        self,
        bucket: BucketName,
        objects_info: BaseListObjectsInfo,
        prefix: Key | None = None,
        delimiter: str | None = None,
        max_keys: MaxKeys = constants.MAX_KEYS,
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

    @tracer.start_as_current_span("get_object")
    async def get_object(
        self,
        bucket: BucketName,
        key: Key,
        range_header: str | None = None,
    ) -> StreamingResponse:
        obj = await self.store.get_object(bucket, key)
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

        filename = os.path.basename(key)
        headers: dict[str, str] = {
            "Content-Length": str(len(data)),
            "Content-Disposition": f'attachment; filename="{filename}"',
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

    @tracer.start_as_current_span("head_object")
    async def head_object(self, bucket: BucketName, key: Key) -> Response:
        metadata = await self.store.head_object(bucket, key)
        return Response(
            status_code=status.HTTP_200_OK,
            headers={
                "Content-Length": str(metadata.size),
                "ETag": f'"{metadata.etag}"',
                "Last-Modified": metadata.last_modified.strftime("%a, %d %b %Y %H:%M:%S GMT"),
                "Content-Type": metadata.content_type,
                "Accept-Ranges": "bytes",
            },
        )

    @tracer.start_as_current_span("put_object")
    async def put_object(
        self,
        bucket: BucketName,
        key: Key,
        content: bytes,
        content_type: ContentType | None = None,
    ) -> Response:
        final_content_type = content_type or constants.DEFAULT_CONTENT_TYPE
        result_etag = await self.store.put_object(bucket, key, content, final_content_type)
        return Response(status_code=status.HTTP_200_OK, headers={"ETag": f'"{result_etag}"'})

    @tracer.start_as_current_span("delete_object")
    async def delete_object(self, bucket: BucketName, key: Key) -> Response:
        try:
            await self.store.delete_object(bucket, key)
        except exceptions.NoSuchBucket:
            logger.info("Bucket %s not found", bucket)
        except exceptions.NoSuchKey:
            logger.info("Object %s not found in bucket %s", key, bucket)
        return Response(
            status_code=status.HTTP_204_NO_CONTENT,
            headers={
                "content-length": "0",
            },
        )

    @tracer.start_as_current_span("create_bucket")
    async def create_bucket(self, bucket: BucketName) -> Response:
        await self.store.create_bucket(bucket)
        return Response(status_code=status.HTTP_200_OK, headers={"Location": f"/{bucket}"})

    @tracer.start_as_current_span("delete_bucket")
    async def delete_bucket(self, bucket: BucketName) -> Response:
        try:
            await self.store.delete_bucket(bucket)
        except exceptions.NoSuchBucket:
            logger.info("Bucket %s not found", bucket)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
