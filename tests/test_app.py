"""Tests for the refactored app with handlers."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from boxdrive import MemoryStore, constants, create_app


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

    s3_ns = {"s3": constants.S3_XML_NAMESPACE}

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


def test_list_buckets_and_create_bucket(client: TestClient) -> None:
    """Test listing buckets functionality."""
    # Initially no buckets
    response = client.get("/buckets")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/xml"

    import xml.etree.ElementTree as ET

    root = ET.fromstring(response.content.decode())
    s3_ns = {"s3": constants.S3_XML_NAMESPACE}

    # Check owner information
    owner = root.find("s3:Owner", s3_ns)
    assert owner is not None
    owner_id = owner.find("s3:ID", s3_ns)
    owner_display_name = owner.find("s3:DisplayName", s3_ns)
    assert owner_id is not None and owner_id.text == constants.OWNER_ID
    assert owner_display_name is not None and owner_display_name.text == constants.OWNER_DISPLAY_NAME

    # Check buckets element exists but is empty initially
    buckets = root.find("s3:Buckets", s3_ns)
    assert buckets is not None
    bucket_list = buckets.findall("s3:Bucket", s3_ns)
    assert len(bucket_list) == 0

    # Create a bucket
    bucket_name = "test-bucket-for-listing"
    response = client.post(f"/{bucket_name}")
    assert response.status_code == 200

    # List buckets again - should now show the created bucket
    response = client.get("/buckets")
    assert response.status_code == 200

    root = ET.fromstring(response.content.decode())
    buckets = root.find("s3:Buckets", s3_ns)
    assert buckets is not None
    bucket_list = buckets.findall("s3:Bucket", s3_ns)
    assert len(bucket_list) == 1

    bucket_name_elem = bucket_list[0].find("s3:Name", s3_ns)
    creation_date_elem = bucket_list[0].find("s3:CreationDate", s3_ns)
    assert bucket_name_elem is not None and bucket_name_elem.text == bucket_name
    assert creation_date_elem is not None and creation_date_elem.text is not None
