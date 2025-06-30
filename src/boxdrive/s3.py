import logging
from collections.abc import AsyncIterator

from fastapi import HTTPException, Response
from fastapi.responses import StreamingResponse

from . import constants, exceptions
from .schemas import BucketName, ContentType, Key, MaxKeys
from .schemas.xml import (
    BucketsXml,
    BucketXml,
    ContentsXml,
    ListAllMyBucketsResultXml,
    ListBucketResultXml,
    OwnerShortXml,
    OwnerXml,
)
from .store import ObjectStore

logger = logging.getLogger(__name__)


class S3:
    def __init__(self, store: ObjectStore):
        self.store = store

    async def list_buckets(self) -> ListAllMyBucketsResultXml:
        buckets = await self.store.list_buckets()
        buckets_xml = [BucketXml(Name=bucket.name, CreationDate=bucket.creation_date.isoformat()) for bucket in buckets]
        owner = OwnerXml(ID=constants.OWNER_ID, DisplayName=constants.OWNER_DISPLAY_NAME)
        buckets_model = BucketsXml(Bucket=buckets_xml)
        return ListAllMyBucketsResultXml(Owner=owner, Buckets=buckets_model)

    async def list_objects(
        self,
        bucket: BucketName,
        prefix: Key | None = None,
        delimiter: str | None = None,
        max_keys: MaxKeys = 1000,
        marker: Key | None = None,
    ) -> ListBucketResultXml:
        objects: list[ContentsXml] = []
        try:
            objects_info = await self.store.list_objects(
                bucket, prefix=prefix, delimiter=delimiter, max_keys=max_keys, marker=marker
            )
        except exceptions.NoSuchBucket:
            logger.info("Bucket %s not found", bucket)
            raise HTTPException(status_code=404, detail="The specified bucket does not exist.")

        for obj in objects_info.objects:
            etag = f'"{obj.etag}"' if obj.etag else ""
            objects.append(
                ContentsXml(
                    Key=obj.key,
                    LastModified=obj.last_modified.isoformat(),
                    ETag=etag,
                    Size=obj.size,
                    StorageClass=constants.DEFAULT_STORAGE_CLASS,
                    Owner=OwnerShortXml(ID=constants.OWNER_ID, DisplayName=constants.OWNER_DISPLAY_NAME),
                )
            )
        return ListBucketResultXml(
            Name=bucket,
            Prefix=prefix or "",
            MaxKeys=max_keys,
            IsTruncated=str(objects_info.is_truncated).lower(),
            Delimiter=delimiter,
            Contents=objects,
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
        metadata = obj.metadata
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
