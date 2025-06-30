"""S3-compatible API handlers for BoxDrive."""

import logging
import xml.etree.ElementTree as ET
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse

from . import constants, exceptions
from .schemas import BucketName, ContentType, Key, MaxKeys
from .store import ObjectStore

router = APIRouter()
logger = logging.getLogger(__name__)


def get_store(request: Request) -> ObjectStore:
    store: ObjectStore = request.app.state.store
    return store


@router.get("/")
async def list_buckets(store: ObjectStore = Depends(get_store)) -> Response:
    """List all buckets in the store."""
    buckets = await store.list_buckets()

    root = ET.Element("ListAllMyBucketsResult", xmlns=constants.S3_XML_NAMESPACE)
    owner = ET.SubElement(root, "Owner")
    ET.SubElement(owner, "ID").text = constants.OWNER_ID
    ET.SubElement(owner, "DisplayName").text = constants.OWNER_DISPLAY_NAME

    buckets_elem = ET.SubElement(root, "Buckets")
    for bucket in buckets:
        bucket_elem = ET.SubElement(buckets_elem, "Bucket")
        ET.SubElement(bucket_elem, "Name").text = bucket.name
        ET.SubElement(bucket_elem, "CreationDate").text = bucket.creation_date.isoformat()

    xml_str = ET.tostring(root, encoding="unicode")
    return Response(content=xml_str, media_type="application/xml")


@router.get("/{bucket}")
async def list_objects(
    bucket: BucketName,
    prefix: Key | None = Query(None),
    delimiter: str | None = Query(None),
    max_keys: MaxKeys | None = Query(1000),
    store: ObjectStore = Depends(get_store),
) -> Response:
    objects: list[dict[str, Any]] = []

    async for obj in store.list_objects(bucket, prefix=prefix, delimiter=delimiter, max_keys=max_keys):
        objects.append(
            {
                "Key": obj.key,
                "Size": obj.size,
                "LastModified": obj.last_modified.isoformat(),
                "ETag": f'"{obj.etag}"' if obj.etag else None,
                "StorageClass": constants.DEFAULT_STORAGE_CLASS,
                "Owner": {"ID": constants.OWNER_ID, "DisplayName": constants.OWNER_DISPLAY_NAME},
            }
        )

    root = ET.Element("ListBucketResult", xmlns=constants.S3_XML_NAMESPACE)
    ET.SubElement(root, "Name").text = bucket
    ET.SubElement(root, "Prefix").text = prefix or ""
    ET.SubElement(root, "MaxKeys").text = str(max_keys)
    ET.SubElement(root, "IsTruncated").text = "false"

    if delimiter:
        ET.SubElement(root, "Delimiter").text = delimiter

    for obj_dict in objects:
        contents = ET.SubElement(root, "Contents")
        ET.SubElement(contents, "Key").text = str(obj_dict["Key"])
        ET.SubElement(contents, "LastModified").text = str(obj_dict["LastModified"])
        ET.SubElement(contents, "ETag").text = str(obj_dict["ETag"])
        ET.SubElement(contents, "Size").text = str(obj_dict["Size"])
        ET.SubElement(contents, "StorageClass").text = str(obj_dict["StorageClass"])

        owner = ET.SubElement(contents, "Owner")
        owner_dict = obj_dict["Owner"]
        if isinstance(owner_dict, dict):
            ET.SubElement(owner, "ID").text = str(owner_dict["ID"])
            ET.SubElement(owner, "DisplayName").text = str(owner_dict["DisplayName"])

    xml_str = ET.tostring(root, encoding="unicode")

    return Response(content=xml_str, media_type="application/xml", headers={"Content-Type": "application/xml"})


@router.get("/{bucket}/{key:path}")
async def get_object(
    bucket: BucketName,
    key: Key,
    range_header: str | None = Header(None, alias="Range"),
    store: ObjectStore = Depends(get_store),
) -> StreamingResponse:
    obj = await store.get_object(bucket, key)
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


@router.head("/{bucket}/{key:path}")
async def head_object(bucket: BucketName, key: Key, store: ObjectStore = Depends(get_store)) -> Response:
    metadata = await store.head_object(bucket, key)
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


@router.put("/{bucket}/{key:path}")
async def put_object(
    bucket: BucketName,
    key: Key,
    request: Request,
    content_type: ContentType | None = Header(None),
    store: ObjectStore = Depends(get_store),
) -> Response:
    content = await request.body()
    final_content_type = content_type or constants.DEFAULT_CONTENT_TYPE
    result_etag = await store.put_object(bucket, key, content, final_content_type)

    return Response(status_code=200, headers={"ETag": f'"{result_etag}"', "Content-Length": "0"})


@router.delete("/{bucket}/{key:path}")
async def delete_object(bucket: BucketName, key: Key, store: ObjectStore = Depends(get_store)) -> Response:
    try:
        await store.delete_object(bucket, key)
    except exceptions.NoSuchBucket:
        logger.info("Bucket %s not found", bucket)
    except exceptions.NoSuchKey:
        logger.info("Object %s not found in bucket %s", key, bucket)

    root = ET.Element("DeleteResult", xmlns=constants.S3_XML_NAMESPACE)
    deleted = ET.SubElement(root, "Deleted")
    ET.SubElement(deleted, "Key").text = key
    ET.SubElement(deleted, "VersionId").text = "null"
    xml_str = ET.tostring(root, encoding="unicode")
    return Response(content=xml_str, media_type="application/xml", status_code=204)


@router.put("/{bucket}")
async def create_bucket(bucket: BucketName, store: ObjectStore = Depends(get_store)) -> Response:
    try:
        await store.create_bucket(bucket)
    except exceptions.BucketAlreadyExists:
        raise HTTPException(status_code=409, detail="Bucket already exists")
    return Response(status_code=200, headers={"Location": f"/{bucket}"})


@router.delete("/{bucket}")
async def delete_bucket(bucket: BucketName, store: ObjectStore = Depends(get_store)) -> Response:
    try:
        await store.delete_bucket(bucket)
    except exceptions.NoSuchBucket:
        logger.info("Bucket %s not found", bucket)
    return Response(status_code=204)
