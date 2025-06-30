"""End-to-end tests using boto3 to verify S3 compatibility."""

import os
from typing import Any

import boto3
import pytest
from botocore.client import Config

BotoClient = Any


@pytest.fixture
def _s3_client() -> BotoClient:
    """Create a boto3 S3 client."""
    endpoint_url = os.getenv("S3_ENDPOINT_URL")
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="us-east-1",
        config=Config(signature_version="s3v4"),
    )


@pytest.fixture
def s3_client(_s3_client: BotoClient) -> BotoClient:
    buckets = _s3_client.list_buckets()
    for bucket in buckets["Buckets"]:
        _s3_client.delete_bucket(Bucket=bucket["Name"])

    buckets = _s3_client.list_buckets()["Buckets"]
    assert len(buckets) == 0
    return _s3_client


def test_boto_list_buckets(s3_client: BotoClient) -> None:
    """Test listing buckets using boto3."""
    s3_client.create_bucket(Bucket="test-bucket-1")
    s3_client.create_bucket(Bucket="test-bucket-2")

    response = s3_client.list_buckets()
    bucket_names = [bucket["Name"] for bucket in response["Buckets"]]
    assert "test-bucket-1" in bucket_names
    assert "test-bucket-2" in bucket_names


def test_boto_put_and_get_object(s3_client: BotoClient) -> None:
    """Test putting and getting objects using boto3."""
    bucket_name = "test-boto-bucket"
    key = "test-file.txt"
    content = b"Hello from boto3!"

    s3_client.create_bucket(Bucket=bucket_name)

    s3_client.put_object(Bucket=bucket_name, Key=key, Body=content, ContentType="text/plain")

    response = s3_client.get_object(Bucket=bucket_name, Key=key)
    retrieved_content = response["Body"].read()

    assert retrieved_content == content
    assert response["ContentType"] == "text/plain"

    """Test listing objects using boto3."""
    bucket_name = "test-list-bucket"

    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.put_object(Bucket=bucket_name, Key="file1.txt", Body=b"content1", ContentType="text/plain")
    s3_client.put_object(Bucket=bucket_name, Key="file2.txt", Body=b"content2", ContentType="text/plain")
    s3_client.put_object(Bucket=bucket_name, Key="folder/file3.txt", Body=b"content3", ContentType="text/plain")

    response = s3_client.list_objects_v2(Bucket=bucket_name)

    keys = [obj["Key"] for obj in response["Contents"]]
    assert "file1.txt" in keys
    assert "file2.txt" in keys
    assert "folder/file3.txt" in keys


def test_boto_head_object(s3_client: BotoClient) -> None:
    """Test head object operation using boto3."""
    bucket_name = "test-head-bucket"
    key = "test-head-file.txt"
    content = b"Test content for head operation"

    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.put_object(Bucket=bucket_name, Key=key, Body=content, ContentType="text/plain")

    response = s3_client.head_object(Bucket=bucket_name, Key=key)
    assert response["ContentLength"] == len(content)
    assert response["ContentType"] == "text/plain"
    assert "ETag" in response


def test_boto_delete_object(s3_client: BotoClient) -> None:
    """Test deleting objects using boto3."""
    bucket_name = "test-delete-bucket"
    key = "test-delete-file.txt"

    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.put_object(Bucket=bucket_name, Key=key, Body=b"content", ContentType="text/plain")

    s3_client.head_object(Bucket=bucket_name, Key=key)

    s3_client.delete_object(Bucket=bucket_name, Key=key)

    with pytest.raises(Exception):  # missing object
        s3_client.head_object(Bucket=bucket_name, Key=key)


def test_boto_range_request(s3_client: BotoClient) -> None:
    """Test range requests using boto3."""
    bucket_name = "test-range-bucket"
    key = "test-range-file.txt"
    content = b"Hello World! This is a test file for range requests."

    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.put_object(Bucket=bucket_name, Key=key, Body=content, ContentType="text/plain")

    response = s3_client.get_object(Bucket=bucket_name, Key=key, Range="bytes=0-4")

    retrieved_content = response["Body"].read()
    assert retrieved_content == b"Hello"
    assert response["ContentRange"] == f"bytes 0-4/{len(content)}"


def test_boto_create_bucket(s3_client: BotoClient) -> None:
    """Test creating buckets using boto3."""
    bucket_name = "new-boto-bucket"

    _ = s3_client.create_bucket(Bucket=bucket_name)

    buckets_response = s3_client.list_buckets()
    bucket_names = [bucket["Name"] for bucket in buckets_response["Buckets"]]
    assert bucket_name in bucket_names


def test_boto_delete_bucket(s3_client: BotoClient) -> None:
    """Test deleting buckets using boto3."""
    bucket_name = "delete-boto-bucket"

    s3_client.create_bucket(Bucket=bucket_name)

    buckets_response = s3_client.list_buckets()
    bucket_names = [bucket["Name"] for bucket in buckets_response["Buckets"]]
    assert bucket_name in bucket_names

    s3_client.delete_bucket(Bucket=bucket_name)

    buckets_response = s3_client.list_buckets()
    bucket_names = [bucket["Name"] for bucket in buckets_response["Buckets"]]
    assert bucket_name not in bucket_names
