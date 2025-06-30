"""In-memory implementation of ObjectStore for testing and development."""

import hashlib
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from .store import ObjectMetadata, ObjectStore


class MemoryStore(ObjectStore):
    """In-memory object store implementation."""

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}
        self._metadata: dict[str, ObjectMetadata] = {}
        self._created_at: dict[str, datetime] = {}

    async def list_objects(
        self, prefix: str | None = None, delimiter: str | None = None, max_keys: int | None = None
    ) -> AsyncIterator[ObjectMetadata]:
        keys = list(self._objects.keys())

        if prefix:
            keys = [k for k in keys if k.startswith(prefix)]

        if max_keys:
            keys = keys[:max_keys]

        for key in keys:
            if key in self._metadata:
                yield self._metadata[key]

    async def get_object(self, key: str) -> bytes | None:
        """Get an object by key."""
        return self._objects.get(key)

    async def put_object(self, key: str, data: bytes, content_type: str | None = None) -> str:
        """Put an object into the store."""
        now = datetime.now(UTC)
        etag = hashlib.md5(data).hexdigest()
        metadata = ObjectMetadata(key=key, size=len(data), last_modified=now, etag=etag, content_type=content_type)

        self._objects[key] = data
        self._metadata[key] = metadata
        self._created_at[key] = now
        return etag

    async def delete_object(self, key: str) -> bool:
        """Delete an object from the store."""
        if key in self._objects:
            del self._objects[key]
            del self._metadata[key]
            if key in self._created_at:
                del self._created_at[key]
            return True
        return False

    async def head_object(self, key: str) -> ObjectMetadata | None:
        """Get object metadata without downloading the content."""
        return self._metadata.get(key)

    async def object_exists(self, key: str) -> bool:
        """Check if an object exists."""
        return key in self._objects

    async def get_object_stream(self, key: str) -> AsyncIterator[bytes] | None:
        """Get an object as a stream."""
        if key not in self._objects:
            return None

        data = self._objects[key]

        async def stream() -> AsyncIterator[bytes]:
            chunk_size = 8192
            for i in range(0, len(data), chunk_size):
                yield data[i : i + chunk_size]

        return stream()

    async def put_object_stream(self, key: str, stream: AsyncIterator[bytes], content_type: str | None = None) -> str:
        """Put an object from a stream."""
        chunks: list[bytes] = []
        async for chunk in stream:
            chunks.append(chunk)

        data = b"".join(chunks)
        return await self.put_object(key, data, content_type)
