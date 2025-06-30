"""In-memory implementation of ObjectStore for testing and development."""

import datetime
import hashlib
from collections.abc import AsyncIterator

from . import constants
from .schemas import BucketMetadata, ContentType, ETag, Key, MaxKeys, ObjectMetadata
from .store import ObjectStore


class MemoryStore(ObjectStore):
    """In-memory object store implementation."""

    def __init__(self) -> None:
        self._objects: dict[Key, bytes] = {}
        self._metadata: dict[Key, ObjectMetadata] = {}
        self._created_at: dict[Key, datetime.datetime] = {}
        self._buckets: dict[str, datetime.datetime] = {}

    async def list_buckets(self) -> list[BucketMetadata]:
        """List all buckets in the store."""
        buckets = []
        for bucket_name, creation_date in self._buckets.items():
            buckets.append(BucketMetadata(name=bucket_name, creation_date=creation_date))
        return buckets

    async def create_bucket(self, bucket_name: str) -> bool:
        """Create a new bucket in the store."""
        if bucket_name in self._buckets:
            return False
        self._buckets[bucket_name] = datetime.datetime.now(datetime.UTC)
        return True

    async def list_objects(
        self, prefix: Key | None = None, delimiter: str | None = None, max_keys: MaxKeys | None = None
    ) -> AsyncIterator[ObjectMetadata]:
        keys = list(self._objects.keys())

        if prefix:
            keys = [k for k in keys if k.startswith(prefix)]

        if max_keys:
            keys = keys[:max_keys]

        for key in keys:
            if key in self._metadata:
                yield self._metadata[key]

    async def get_object(self, key: Key) -> bytes | None:
        """Get an object by key."""
        return self._objects.get(key)

    async def put_object(self, key: Key, data: bytes, content_type: ContentType | None = None) -> ETag:
        """Put an object into the store."""
        now = datetime.datetime.now(datetime.UTC)
        etag = hashlib.md5(data).hexdigest()
        final_content_type = content_type or constants.DEFAULT_CONTENT_TYPE
        metadata = ObjectMetadata(
            key=key, size=len(data), last_modified=now, etag=etag, content_type=final_content_type
        )

        self._objects[key] = data
        self._metadata[key] = metadata
        self._created_at[key] = now
        return etag

    async def delete_object(self, key: Key) -> bool:
        """Delete an object from the store."""
        if key in self._objects:
            del self._objects[key]
            del self._metadata[key]
            if key in self._created_at:
                del self._created_at[key]
            return True
        return False

    async def head_object(self, key: Key) -> ObjectMetadata | None:
        """Get object metadata without downloading the content."""
        return self._metadata.get(key)

    async def object_exists(self, key: Key) -> bool:
        """Check if an object exists."""
        return key in self._objects

    async def get_object_stream(self, key: Key) -> AsyncIterator[bytes] | None:
        """Get an object as a stream."""
        if key not in self._objects:
            return None

        data = self._objects[key]

        async def stream() -> AsyncIterator[bytes]:
            for i in range(0, len(data), constants.STREAM_CHUNK_SIZE):
                yield data[i : i + constants.STREAM_CHUNK_SIZE]

        return stream()

    async def put_object_stream(
        self, key: Key, stream: AsyncIterator[bytes], content_type: ContentType | None = None
    ) -> ETag:
        """Put an object from a stream."""
        chunks: list[bytes] = []
        async for chunk in stream:
            chunks.append(chunk)

        data = b"".join(chunks)
        return await self.put_object(key, data, content_type)
