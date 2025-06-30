"""S3-compatible API handlers for BoxDrive."""

import hashlib
import xml.etree.ElementTree as ET
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import StreamingResponse

from .store import ObjectStore

router = APIRouter()


def get_store(request: Request) -> ObjectStore:
    store: ObjectStore = request.app.state.store
    return store


@router.get("/")
async def root() -> dict[str, str]:
    return {"message": "BoxDrive S3-compatible API", "status": "healthy"}


@router.get("/{bucket}")
async def list_objects(
    bucket: str,
    prefix: str | None = Query(None),
    delimiter: str | None = Query(None),
    max_keys: int | None = Query(1000),
    continuation_token: str | None = Query(None),
    start_after: str | None = Query(None),
    store: ObjectStore = Depends(get_store),
) -> Response:
    try:
        objects: list[dict[str, object]] = []

        async for obj in store.list_objects(prefix=prefix, delimiter=delimiter, max_keys=max_keys):
            objects.append(
                {
                    "Key": obj.key,
                    "Size": obj.size,
                    "LastModified": obj.last_modified.isoformat(),
                    "ETag": f'"{obj.etag}"' if obj.etag else None,
                    "StorageClass": "STANDARD",
                    "Owner": {"ID": "boxdrive", "DisplayName": "BoxDrive"},
                }
            )

        root = ET.Element("ListBucketResult", xmlns="http://s3.amazonaws.com/doc/2006-03-01/")
        ET.SubElement(root, "Name").text = bucket
        ET.SubElement(root, "Prefix").text = prefix or ""
        ET.SubElement(root, "MaxKeys").text = str(max_keys)
        ET.SubElement(root, "IsTruncated").text = "false"

        if delimiter:
            ET.SubElement(root, "Delimiter").text = delimiter

        if continuation_token:
            ET.SubElement(root, "NextContinuationToken").text = continuation_token

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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{bucket}/{key:path}")
async def get_object(
    bucket: str,
    key: str,
    range_header: str | None = Header(None, alias="Range"),
    store: ObjectStore = Depends(get_store),
) -> StreamingResponse:
    try:
        metadata = await store.head_object(key)
        if not metadata:
            raise HTTPException(status_code=404, detail="Object not found")

        data = await store.get_object(key)
        if data is None:
            raise HTTPException(status_code=404, detail="Object not found")

        start = 0
        end = len(data) - 1
        original_size = len(data)

        if range_header:
            try:
                range_str = range_header.replace("bytes=", "")
                if "-" in range_str:
                    start_str, end_str = range_str.split("-", 1)
                    start = int(start_str) if start_str else 0
                    end = int(end_str) if end_str else len(data) - 1
                    data = data[start : end + 1]
            except (ValueError, IndexError):
                pass

        async def generate() -> AsyncIterator[bytes]:
            yield data

        headers: dict[str, str] = {
            "Content-Length": str(len(data)),
            "ETag": f'"{metadata.etag}"' if metadata.etag else "",
            "Last-Modified": metadata.last_modified.strftime("%a, %d %b %Y %H:%M:%S GMT"),
            "Content-Type": metadata.content_type or "application/octet-stream",
            "Accept-Ranges": "bytes",
        }

        if range_header:
            headers["Content-Range"] = f"bytes {start}-{end}/{original_size}"
            status_code = 206
        else:
            status_code = 200

        return StreamingResponse(
            generate(),
            media_type=metadata.content_type or "application/octet-stream",
            headers=headers,
            status_code=status_code,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.head("/{bucket}/{key:path}")
async def head_object(bucket: str, key: str, store: ObjectStore = Depends(get_store)) -> Response:
    try:
        metadata = await store.head_object(key)
        if not metadata:
            raise HTTPException(status_code=404, detail="Object not found")

        return Response(
            status_code=200,
            headers={
                "Content-Length": str(metadata.size),
                "ETag": f'"{metadata.etag}"' if metadata.etag else "",
                "Last-Modified": metadata.last_modified.strftime("%a, %d %b %Y %H:%M:%S GMT"),
                "Content-Type": metadata.content_type or "application/octet-stream",
                "Accept-Ranges": "bytes",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{bucket}/{key:path}")
async def put_object(
    bucket: str,
    key: str,
    file: UploadFile = File(...),
    content_type: str | None = None,
    store: ObjectStore = Depends(get_store),
) -> Response:
    try:
        content = await file.read()
        final_content_type = content_type or file.content_type
        result_etag = await store.put_object(key, content, final_content_type)

        return Response(status_code=200, headers={"ETag": f'"{result_etag}"', "Content-Length": "0"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{bucket}/{key:path}")
async def delete_object(bucket: str, key: str, store: ObjectStore = Depends(get_store)) -> Response:
    try:
        success = await store.delete_object(key)
        if not success:
            raise HTTPException(status_code=404, detail="Object not found")

        root = ET.Element("DeleteResult", xmlns="http://s3.amazonaws.com/doc/2006-03-01/")
        deleted = ET.SubElement(root, "Deleted")
        ET.SubElement(deleted, "Key").text = key
        ET.SubElement(deleted, "VersionId").text = "null"

        xml_str = ET.tostring(root, encoding="unicode")

        return Response(content=xml_str, media_type="application/xml", status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{bucket}")
async def create_bucket(bucket: str, store: ObjectStore = Depends(get_store)) -> Response:
    return Response(status_code=200, headers={"Location": f"/{bucket}"})


@router.delete("/{bucket}")
async def delete_bucket(bucket: str, store: ObjectStore = Depends(get_store)) -> Response:
    return Response(status_code=204)


@router.post("/{bucket}/{key:path}")
async def initiate_multipart_upload(
    bucket: str, key: str, uploads: str | None = Query(None), store: ObjectStore = Depends(get_store)
) -> Response:
    if uploads:
        upload_id = f"upload-{hashlib.md5(f'{bucket}-{key}-{datetime.now(UTC)}'.encode()).hexdigest()}"

        root = ET.Element("InitiateMultipartUploadResult", xmlns="http://s3.amazonaws.com/doc/2006-03-01/")
        ET.SubElement(root, "Bucket").text = bucket
        ET.SubElement(root, "Key").text = key
        ET.SubElement(root, "UploadId").text = upload_id

        xml_str = ET.tostring(root, encoding="unicode")

        return Response(content=xml_str, media_type="application/xml")

    return Response(status_code=200)
