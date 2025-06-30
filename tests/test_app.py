"""Tests for the refactored app with handlers."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from boxdrive import MemoryStore, create_app


@pytest.fixture
def store() -> MemoryStore:
    return MemoryStore()


@pytest.fixture
def app(store: MemoryStore) -> FastAPI:
    return create_app(store)


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def test_root_endpoint(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "BoxDrive S3-compatible API"
    assert data["status"] == "healthy"


def test_put_and_get_object(client: TestClient) -> None:
    bucket = "test-bucket"
    key = "test.txt"
    content = b"Hello, World!"

    response = client.put(f"/{bucket}/{key}", files={"file": ("test.txt", content, "text/plain")})
    assert response.status_code == 200
    assert "ETag" in response.headers

    response = client.get(f"/{bucket}/{key}")
    assert response.status_code == 200
    assert response.content == content
    assert response.headers["Content-Type"] == "text/plain"


def test_head_object(client: TestClient) -> None:
    bucket = "test-bucket"
    key = "test.txt"
    content = b"Hello, World!"

    client.put(f"/{bucket}/{key}", files={"file": ("test.txt", content, "text/plain")})

    response = client.head(f"/{bucket}/{key}")
    assert response.status_code == 200
    assert "Content-Length" in response.headers
    assert "ETag" in response.headers
    assert "Last-Modified" in response.headers
    assert "Accept-Ranges" in response.headers


def test_delete_object(client: TestClient) -> None:
    bucket = "test-bucket"
    key = "test.txt"
    content = b"Hello, World!"

    client.put(f"/{bucket}/{key}", files={"file": ("test.txt", content, "text/plain")})

    response = client.get(f"/{bucket}/{key}")
    assert response.status_code == 200

    response = client.delete(f"/{bucket}/{key}")
    assert response.status_code == 204

    response = client.get(f"/{bucket}/{key}")
    assert response.status_code == 404


def test_list_objects(client: TestClient) -> None:
    bucket = "test-bucket"

    test_objects = [
        ("file1.txt", b"content1"),
        ("file2.txt", b"content2"),
        ("folder/file3.txt", b"content3"),
    ]

    for obj_key, obj_content in test_objects:
        client.put(f"/{bucket}/{obj_key}", files={"file": (obj_key, obj_content, "text/plain")})

    response = client.get(f"/{bucket}")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/xml"

    import xml.etree.ElementTree as ET

    root = ET.fromstring(response.content.decode())

    s3_ns = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}

    contents = root.findall(".//s3:Contents", s3_ns)
    assert len(contents) == 3

    keys = []
    for content in contents:
        key_elem = content.find("s3:Key", s3_ns)
        if key_elem is not None and key_elem.text is not None:
            keys.append(key_elem.text)

    assert "file1.txt" in keys
    assert "file2.txt" in keys
    assert "folder/file3.txt" in keys


def test_range_request(client: TestClient) -> None:
    bucket = "test-bucket"
    key = "test.txt"
    content = b"Hello, World! This is a test file."

    client.put(f"/{bucket}/{key}", files={"file": (key, content, "text/plain")})

    response = client.get(f"/{bucket}/{key}", headers={"Range": "bytes=0-4"})
    assert response.status_code == 206
    assert response.content == b"Hello"
    assert "Content-Range" in response.headers
    assert response.headers["Content-Range"] == "bytes 0-4/34"


def test_create_bucket(client: TestClient) -> None:
    bucket = "new-bucket"

    response = client.post(f"/{bucket}")
    assert response.status_code == 200
    assert "Location" in response.headers
    assert response.headers["Location"] == f"/{bucket}"


def test_delete_bucket(client: TestClient) -> None:
    bucket = "test-bucket"

    response = client.delete(f"/{bucket}")
    assert response.status_code == 204


def test_initiate_multipart_upload(client: TestClient) -> None:
    bucket = "test-bucket"
    key = "large-file.txt"

    # Test with uploads parameter (any value)
    response = client.post(f"/{bucket}/{key}?uploads=true")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/xml"

    # Parse XML response
    import xml.etree.ElementTree as ET

    root = ET.fromstring(response.content.decode())
    s3_ns = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}

    bucket_elem = root.find("s3:Bucket", s3_ns)
    key_elem = root.find("s3:Key", s3_ns)
    upload_id_elem = root.find("s3:UploadId", s3_ns)

    assert bucket_elem is not None and bucket_elem.text == bucket
    assert key_elem is not None and key_elem.text == key
    assert upload_id_elem is not None
    assert upload_id_elem.text is not None
    assert upload_id_elem.text.startswith("upload-")

    # Test without uploads parameter
    response = client.post(f"/{bucket}/{key}")
    assert response.status_code == 200
