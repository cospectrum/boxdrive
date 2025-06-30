"""S3-compatible API handlers for BoxDrive."""

import logging
from typing import Literal

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from fastapi.responses import StreamingResponse

from .s3 import S3
from .schemas import BucketName, ContentType, Key, MaxKeys
from .schemas.xml import XMLResponse
from .store import ObjectStore

router = APIRouter()
logger = logging.getLogger(__name__)


def get_store(request: Request) -> ObjectStore:
    store: ObjectStore = request.app.state.store
    return store


def get_s3(request: Request) -> S3:
    return S3(get_store(request))


@router.get("/")
async def list_buckets(s3: S3 = Depends(get_s3)) -> XMLResponse:
    buckets = await s3.list_buckets()
    return XMLResponse(buckets)


ListType = Literal["1", "2"]


@router.get("/{bucket}")
async def list_objects(
    bucket: BucketName,
    prefix: Key | None = Query(None),
    delimiter: str | None = Query(None),
    max_keys: MaxKeys = Query(1000, alias="max-keys"),
    marker: Key | None = Query(None),
    continuation_token: Key | None = Query(None, alias="continuation-token"),
    start_after: Key | None = Query(None, alias="start-after"),
    list_type: ListType = Query("1", alias="list-type"),
    s3: S3 = Depends(get_s3),
) -> XMLResponse:
    if list_type == "1":
        objects = await s3.list_objects(bucket, prefix=prefix, delimiter=delimiter, max_keys=max_keys, marker=marker)
    else:
        objects = await s3.list_objects_v2(
            bucket,
            prefix=prefix,
            delimiter=delimiter,
            max_keys=max_keys,
            continuation_token=continuation_token,
            start_after=start_after,
        )
    return XMLResponse(objects)


@router.get("/{bucket}/{key:path}")
async def get_object(
    bucket: BucketName,
    key: Key,
    range_header: str | None = Header(None, alias="Range"),
    s3: S3 = Depends(get_s3),
) -> StreamingResponse:
    return await s3.get_object(bucket, key, range_header=range_header)


@router.head("/{bucket}/{key:path}")
async def head_object(bucket: BucketName, key: Key, s3: S3 = Depends(get_s3)) -> Response:
    return await s3.head_object(bucket, key)


@router.put("/{bucket}/{key:path}")
async def put_object(
    bucket: BucketName,
    key: Key,
    request: Request,
    content_type: ContentType | None = Header(None),
    s3: S3 = Depends(get_s3),
) -> Response:
    content = await request.body()
    return await s3.put_object(bucket, key, content, content_type)


@router.delete("/{bucket}/{key:path}")
async def delete_object(bucket: BucketName, key: Key, s3: S3 = Depends(get_s3)) -> XMLResponse:
    await s3.delete_object(bucket, key)
    return XMLResponse(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{bucket}")
async def create_bucket(bucket: BucketName, s3: S3 = Depends(get_s3)) -> Response:
    return await s3.create_bucket(bucket)


@router.delete("/{bucket}")
async def delete_bucket(bucket: BucketName, s3: S3 = Depends(get_s3)) -> Response:
    return await s3.delete_bucket(bucket)
