import asyncio
import os
import random
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

import httpx
import pytest

S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")
NUM_OPS = int(os.getenv("NUM_OPS", "100"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "5"))


async def run_in_batches(
    func: Callable[[], Awaitable[Any]],
    num_ops: int,
    batch_size: int,
) -> None:
    for i in range(0, num_ops, batch_size):
        batch = [func() for _ in range(min(batch_size, num_ops - i))]
        await asyncio.gather(*batch)


@pytest.fixture
async def async_client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(base_url=S3_ENDPOINT_URL, timeout=10.0) as client:
        yield client


async def test_concurrent_put_and_get(async_client: httpx.AsyncClient) -> None:
    BUCKET = "concurrent-bucket-put-get"
    KEYS = [f"file_{i}.txt" for i in range(BATCH_SIZE)]
    await async_client.put(f"/{BUCKET}")

    async def put(key: str) -> None:
        content = os.urandom(32)
        r = await async_client.put(
            f"/{BUCKET}/{key}",
            content=content,
            headers={"Content-Type": "application/octet-stream"},
        )
        assert r.status_code != 500, f"500 on PUT {key}: {r.text}"

    async def get(key: str) -> None:
        r = await async_client.get(f"/{BUCKET}/{key}")
        assert r.status_code != 500, f"500 on GET {key}: {r.text}"

    async def put_and_get_pair() -> None:
        key = random.choice(KEYS)
        await asyncio.gather(put(key), get(key))

    await run_in_batches(put_and_get_pair, NUM_OPS, BATCH_SIZE)


async def test_concurrent_delete_and_head(async_client: httpx.AsyncClient) -> None:
    BUCKET = "concurrent-bucket-delete-head"
    KEYS = [f"file_{i}.txt" for i in range(BATCH_SIZE)]
    await async_client.put(f"/{BUCKET}")
    for key in KEYS:
        await async_client.put(
            f"/{BUCKET}/{key}",
            content=b"init",
            headers={"Content-Type": "application/octet-stream"},
        )

    async def delete(key: str) -> None:
        r = await async_client.delete(f"/{BUCKET}/{key}")
        assert r.status_code != 500, f"500 on DELETE {key}: {r.text}"

    async def head(key: str) -> None:
        r = await async_client.head(f"/{BUCKET}/{key}")
        assert r.status_code != 500, f"500 on HEAD {key}: {r.text}"

    async def delete_and_head_pair() -> None:
        key = random.choice(KEYS)
        await asyncio.gather(delete(key), head(key))

    await run_in_batches(delete_and_head_pair, NUM_OPS, BATCH_SIZE)


async def test_concurrent_put_and_list(async_client: httpx.AsyncClient) -> None:
    BUCKET = "concurrent-bucket-put-list"
    KEYS = [f"file_{i}.txt" for i in range(BATCH_SIZE)]
    await async_client.put(f"/{BUCKET}")

    async def put(key: str) -> None:
        content = os.urandom(32)
        r = await async_client.put(
            f"/{BUCKET}/{key}",
            content=content,
            headers={"Content-Type": "application/octet-stream"},
        )
        assert r.status_code != 500, f"500 on PUT {key}: {r.text}"

    async def list_objects() -> None:
        r = await async_client.get(f"/{BUCKET}")
        assert r.status_code != 500, f"500 on LIST objects: {r.text}"

    async def put_and_list_pair() -> None:
        key = random.choice(KEYS)
        await asyncio.gather(put(key), list_objects())

    await run_in_batches(put_and_list_pair, NUM_OPS, BATCH_SIZE)


async def test_concurrent_bucket_create_and_list(async_client: httpx.AsyncClient) -> None:
    BUCKETS = [f"concurrent-bucket-{i}" for i in range(BATCH_SIZE)]

    async def create(bucket: str) -> None:
        r = await async_client.put(f"/{bucket}")
        assert r.status_code != 500, f"500 on CREATE BUCKET {bucket}: {r.text}"

    async def list_buckets() -> None:
        r = await async_client.get("/")
        assert r.status_code != 500, f"500 on LIST BUCKETS: {r.text}"

    async def create_and_list_pair() -> None:
        bucket = random.choice(BUCKETS)
        await asyncio.gather(create(bucket), list_buckets())

    await run_in_batches(create_and_list_pair, NUM_OPS, BATCH_SIZE)
