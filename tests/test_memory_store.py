"""Tests for the memory store implementation."""

from collections.abc import AsyncIterator

import pytest

from boxdrive.memory_store import MemoryStore


@pytest.fixture
async def store() -> MemoryStore:
    """Create a fresh memory store for each test."""
    return MemoryStore()


async def test_put_and_get_object(store: MemoryStore) -> None:
    """Test putting and getting an object."""
    key = "test.txt"
    data = b"Hello, World!"
    content_type = "text/plain"

    etag = await store.put_object(key, data, content_type)
    assert etag is not None

    retrieved_data = await store.get_object(key)
    assert retrieved_data == data

    # Check metadata
    metadata = await store.head_object(key)
    assert metadata is not None
    assert metadata.key == key
    assert metadata.size == len(data)
    assert metadata.content_type == content_type
    assert metadata.etag == etag


async def test_object_exists(store: MemoryStore) -> None:
    """Test object existence."""
    key = "test.txt"
    data = b"Hello, World!"

    assert not await store.object_exists(key)
    await store.put_object(key, data)

    assert await store.object_exists(key)


async def test_delete_object(store: MemoryStore) -> None:
    """Test deleting an object."""
    key = "test.txt"
    data = b"Hello, World!"

    await store.put_object(key, data)
    assert await store.object_exists(key)

    success = await store.delete_object(key)
    assert success

    assert not await store.object_exists(key)
    assert await store.get_object(key) is None


async def test_list_objects(store: MemoryStore) -> None:
    """Test listing objects."""
    objects = [
        ("file1.txt", b"content1"),
        ("file2.txt", b"content2"),
        ("folder/file3.txt", b"content3"),
    ]

    for key, data in objects:
        await store.put_object(key, data)

    # List all objects
    all_objects = []
    async for obj in store.list_objects():
        all_objects.append(obj.key)

    assert len(all_objects) == 3
    assert "file1.txt" in all_objects
    assert "file2.txt" in all_objects
    assert "folder/file3.txt" in all_objects

    folder_objects = []
    async for obj in store.list_objects(prefix="folder/"):
        folder_objects.append(obj.key)

    assert len(folder_objects) == 1
    assert "folder/file3.txt" in folder_objects


async def test_get_object_stream(store: MemoryStore) -> None:
    """Test getting object as stream."""
    key = "test.txt"
    data = b"Hello, World! This is a test file with some content."

    await store.put_object(key, data)

    stream = await store.get_object_stream(key)
    assert stream is not None

    chunks = []
    async for chunk in stream:
        chunks.append(chunk)

    retrieved_data = b"".join(chunks)
    assert retrieved_data == data


async def test_put_object_stream(store: MemoryStore) -> None:
    """Test putting object from stream."""
    key = "test.txt"
    data = b"Hello, World! This is a test file with some content."

    async def data_stream() -> AsyncIterator[bytes]:
        chunk_size = 10
        for i in range(0, len(data), chunk_size):
            yield data[i : i + chunk_size]

    etag = await store.put_object_stream(key, data_stream())
    assert etag is not None

    retrieved_data = await store.get_object(key)
    assert retrieved_data == data
