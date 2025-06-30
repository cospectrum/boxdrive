"""Tests for the memory store implementation."""

import pytest

from boxdrive.stores import MemoryStore


@pytest.fixture
async def store() -> MemoryStore:
    return MemoryStore()


async def test_put_and_get_object(store: MemoryStore) -> None:
    BUCKET = "test-bucket"

    key = "test.txt"
    data = b"Hello, World!"
    content_type = "text/plain"
    await store.create_bucket(BUCKET)
    etag = await store.put_object(BUCKET, key, data, content_type)
    obj = await store.get_object(BUCKET, key)
    assert obj is not None
    assert obj.data == data
    metadata = await store.head_object(BUCKET, key)
    assert metadata is not None
    assert metadata.key == key
    assert metadata.size == len(data)
    assert metadata.content_type == content_type
    assert metadata.etag == etag


async def test_delete_object(store: MemoryStore) -> None:
    BUCKET = "test-bucket"

    key = "test.txt"
    data = b"Hello, World!"
    await store.create_bucket(BUCKET)
    await store.put_object(BUCKET, key, data)
    success = await store.delete_object(BUCKET, key)
    assert success
    assert (await store.get_object(BUCKET, key)) is None


async def test_list_objects(store: MemoryStore) -> None:
    BUCKET = "test-bucket"

    await store.create_bucket(BUCKET)
    objects = [
        ("file1.txt", b"content1"),
        ("file2.txt", b"content2"),
        ("folder/file3.txt", b"content3"),
    ]
    for key, data in objects:
        await store.put_object(BUCKET, key, data)
    all_objects = []
    async for obj in store.list_objects(BUCKET):
        all_objects.append(obj.key)
    assert len(all_objects) == 3
    assert "file1.txt" in all_objects
    assert "file2.txt" in all_objects
    assert "folder/file3.txt" in all_objects
    folder_objects = []
    async for obj in store.list_objects(BUCKET, prefix="folder/"):
        folder_objects.append(obj.key)
    assert len(folder_objects) == 1
    assert "folder/file3.txt" in folder_objects


async def test_list_buckets_and_create_bucket(store: MemoryStore) -> None:
    buckets = await store.list_buckets()
    assert len(buckets) == 0
    bucket_names = ["bucket1", "bucket2", "bucket3"]
    for bucket_name in bucket_names:
        success = await store.create_bucket(bucket_name)
        assert success
    buckets = await store.list_buckets()
    assert len(buckets) == 3
    bucket_names_found = [bucket.name for bucket in buckets]
    assert set(bucket_names_found) == set(bucket_names)
    for bucket in buckets:
        assert bucket.creation_date is not None
    success = await store.create_bucket("bucket1")
    assert not success
    buckets = await store.list_buckets()
    assert len(buckets) == 3
