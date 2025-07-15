"""S3-compatible API handlers for BoxDrive."""

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from fastapi.responses import StreamingResponse

from . import (
    constants,
    dependencies as deps,
)
from .s3 import S3
from .schemas import BucketName, ContentType, Key, MaxKeys
from .schemas.xml import XMLResponse

logger = logging.getLogger(__name__)

S3Dep = Annotated[S3, Depends(deps.get_s3)]
router = APIRouter(
    dependencies=[
        Depends(deps.opentelemetry_headers),
    ],
)


@router.get("/")
async def list_buckets(s3: S3Dep) -> XMLResponse:
    buckets = await s3.list_buckets()
    return XMLResponse(buckets)


@router.get("/{bucket}")
async def list_objects(
    bucket: BucketName,
    prefix: Key | None = Query(None),
    delimiter: str | None = Query(None),
    max_keys: MaxKeys = Query(constants.MAX_KEYS, alias="max-keys"),
    marker: Key | None = Query(None),
    continuation_token: Key | None = Query(None, alias="continuation-token"),
    start_after: Key | None = Query(None, alias="start-after"),
    list_type: Literal["1", "2"] = Query("1", alias="list-type"),
    *,
    s3: S3Dep,
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
    *,
    s3: S3Dep,
) -> StreamingResponse:
    return await s3.get_object(bucket, key, range_header=range_header)


@router.head("/{bucket}/{key:path}")
async def head_object(bucket: BucketName, key: Key, s3: S3Dep) -> Response:
    return await s3.head_object(bucket, key)


@router.put(
    "/{bucket}/{key:path}",
    openapi_extra={
        "requestBody": {
            "content": {
                "application/octet-stream": {
                    "schema": {"type": "string", "format": "binary"},
                }
            }
        }
    },
)
async def put_object(
    bucket: BucketName,
    key: Key,
    request: Request,
    content_type: ContentType | None = Header(None),
    *,
    s3: S3Dep,
) -> Response:
    content = await request.body()
    return await s3.put_object(bucket, key, content, content_type)


@router.delete("/{bucket}/{key:path}")
async def delete_object(bucket: BucketName, key: Key, s3: S3Dep) -> Response:
    return await s3.delete_object(bucket, key)


@router.put("/{bucket}")
async def create_bucket(bucket: BucketName, s3: S3Dep) -> Response:
    return await s3.create_bucket(bucket)


@router.delete("/{bucket}")
async def delete_bucket(bucket: BucketName, s3: S3Dep) -> Response:
    return await s3.delete_bucket(bucket)
