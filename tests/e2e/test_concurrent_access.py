import asyncio
import os
import random

import httpx
import pytest

S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")

@pytest.fixture
async def async_client():
    async with httpx.AsyncClient(base_url=S3_ENDPOINT_URL, timeout=10.0) as client:
        yield client

@pytest.mark.asyncio
async def test_concurrent_put_and_get(async_client):
    BUCKET = "concurrent-bucket-put-get"
    KEYS = [f"file_{i}.txt" for i in range(10)]
    NUM_OPS = 500
    await async_client.put(f"/{BUCKET}")

    async def put_object(key: str):
        for _ in range(NUM_OPS):
            content = os.urandom(32)
            r = await async_client.put(
                f"/{BUCKET}/{key}",
                content=content,
                headers={"Content-Type": "application/octet-stream"},
            )
            if r.status_code == 500:
                raise Exception(f"500 on PUT {key}: {r.text}")

    async def get_object(key: str):
        for _ in range(NUM_OPS):
            r = await async_client.get(f"/{BUCKET}/{key}")
            if r.status_code == 500:
                raise Exception(f"500 on GET {key}: {r.text}")

    tasks = []
    for key in KEYS:
        tasks.append(put_object(key))
        tasks.append(get_object(key))
    await asyncio.gather(*tasks)

@pytest.mark.asyncio
async def test_concurrent_delete_and_head(async_client):
    BUCKET = "concurrent-bucket-delete-head"
    KEYS = [f"file_{i}.txt" for i in range(10)]
    NUM_OPS = 500
    await async_client.put(f"/{BUCKET}")
    for key in KEYS:
        await async_client.put(
            f"/{BUCKET}/{key}",
            content=b"init",
            headers={"Content-Type": "application/octet-stream"},
        )

    async def delete_object(key: str):
        for _ in range(NUM_OPS):
            r = await async_client.delete(f"/{BUCKET}/{key}")
            if r.status_code == 500:
                raise Exception(f"500 on DELETE {key}: {r.text}")

    async def head_object(key: str):
        for _ in range(NUM_OPS):
            r = await async_client.head(f"/{BUCKET}/{key}")
            if r.status_code == 500:
                raise Exception(f"500 on HEAD {key}: {r.text}")

    tasks = []
    for key in KEYS:
        tasks.append(delete_object(key))
        tasks.append(head_object(key))
    await asyncio.gather(*tasks)

@pytest.mark.asyncio
async def test_concurrent_put_and_list(async_client):
    BUCKET = "concurrent-bucket-put-list"
    KEYS = [f"file_{i}.txt" for i in range(10)]
    NUM_OPS = 500
    await async_client.put(f"/{BUCKET}")

    async def put_object(key: str):
        for _ in range(NUM_OPS):
            content = os.urandom(32)
            r = await async_client.put(
                f"/{BUCKET}/{key}",
                content=content,
                headers={"Content-Type": "application/octet-stream"},
            )
            if r.status_code == 500:
                raise Exception(f"500 on PUT {key}: {r.text}")

    async def list_objects():
        for _ in range(NUM_OPS):
            r = await async_client.get(f"/{BUCKET}")
            if r.status_code == 500:
                raise Exception(f"500 on LIST objects: {r.text}")

    tasks = []
    for key in KEYS:
        tasks.append(put_object(key))
    tasks.append(list_objects())
    await asyncio.gather(*tasks)

@pytest.mark.asyncio
async def test_concurrent_bucket_create_and_list(async_client):
    BUCKETS = [f"concurrent-bucket-{i}" for i in range(10)]
    NUM_OPS = 500

    async def create_bucket(bucket: str):
        for _ in range(NUM_OPS):
            r = await async_client.put(f"/{bucket}")
            if r.status_code == 500:
                raise Exception(f"500 on CREATE BUCKET {bucket}: {r.text}")

    async def list_buckets():
        for _ in range(NUM_OPS):
            r = await async_client.get("/")
            if r.status_code == 500:
                raise Exception(f"500 on LIST BUCKETS: {r.text}")

    tasks = []
    for bucket in BUCKETS:
        tasks.append(create_bucket(bucket))
    tasks.append(list_buckets())
    await asyncio.gather(*tasks)
