import os
from typing import Any

import boto3
import pytest
from botocore.client import Config

BotoClient = Any


@pytest.fixture
def _s3_client() -> BotoClient:
    endpoint_url = os.environ["S3_ENDPOINT_URL"]
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


def test_create_and_list_bucket(s3_client: BotoClient) -> None:
    bucket = "e2e-bucket"
    s3_client.create_bucket(Bucket=bucket)
    buckets = s3_client.list_buckets()["Buckets"]
    names = [b["Name"] for b in buckets]
    assert bucket in names


@pytest.mark.parametrize(
    ["content", "content_type"],
    [
        (bytes([255, 254]), "application/octet-stream"),
        (b"e2e content", "text/plain"),
    ],
)
def test_put_and_get_object(
    content: bytes,
    content_type: str,
    s3_client: BotoClient,
) -> None:
    bucket = "e2e-bucket"
    key = "file.bin"
    s3_client.create_bucket(Bucket=bucket)
    s3_client.put_object(Bucket=bucket, Key=key, Body=content, ContentType=content_type)
    obj = s3_client.get_object(Bucket=bucket, Key=key)
    assert obj["Body"].read() == content


def test_list_objects(s3_client: BotoClient) -> None:
    bucket = "e2e-bucket"
    s3_client.create_bucket(Bucket=bucket)
    s3_client.put_object(Bucket=bucket, Key="a.txt", Body=b"a")
    s3_client.put_object(Bucket=bucket, Key="b.txt", Body=b"b")
    resp = s3_client.list_objects(Bucket=bucket)
    keys = [obj["Key"] for obj in resp["Contents"]]
    assert set(keys) == {"a.txt", "b.txt"}


def test_head_object(s3_client: BotoClient) -> None:
    bucket = "e2e-bucket"
    key = "head.txt"
    content = b"head content"
    s3_client.create_bucket(Bucket=bucket)
    s3_client.put_object(Bucket=bucket, Key=key, Body=content, ContentType="text/plain")
    meta = s3_client.head_object(Bucket=bucket, Key=key)
    assert meta["ContentLength"] == len(content)
    assert "ContentType" in meta
    assert "ETag" in meta


def test_delete_object(s3_client: BotoClient) -> None:
    bucket = "e2e-bucket"
    key = "del.txt"
    s3_client.create_bucket(Bucket=bucket)
    s3_client.put_object(Bucket=bucket, Key=key, Body=b"del")
    s3_client.delete_object(Bucket=bucket, Key=key)
    with pytest.raises(Exception):
        s3_client.head_object(Bucket=bucket, Key=key)


def test_delete_bucket(s3_client: BotoClient) -> None:
    bucket = "e2e-bucket"
    s3_client.create_bucket(Bucket=bucket)
    s3_client.delete_bucket(Bucket=bucket)
    buckets = s3_client.list_buckets()["Buckets"]
    names = [b["Name"] for b in buckets]
    assert bucket not in names


def test_get_object_range(s3_client: BotoClient) -> None:
    bucket = "e2e-bucket"
    key = "range.txt"
    content = b"0123456789"
    s3_client.create_bucket(Bucket=bucket)
    s3_client.put_object(Bucket=bucket, Key=key, Body=content, ContentType="text/plain")
    resp = s3_client.get_object(Bucket=bucket, Key=key, Range="bytes=2-5")
    assert resp["Body"].read() == b"2345"
    assert resp["ContentRange"] == f"bytes 2-5/{len(content)}"


def test_list_objects_with_prefix(s3_client: BotoClient) -> None:
    bucket = "e2e-bucket"
    s3_client.create_bucket(Bucket=bucket)
    s3_client.put_object(Bucket=bucket, Key="foo/a.txt", Body=b"a")
    s3_client.put_object(Bucket=bucket, Key="foo/b.txt", Body=b"b")
    resp = s3_client.list_objects(Bucket=bucket, Prefix="foo/")
    keys = [obj["Key"] for obj in resp["Contents"]]
    assert set(keys) == {"foo/a.txt", "foo/b.txt"}
