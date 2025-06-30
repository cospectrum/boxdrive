# BoxDrive

S3-compatible API with an **Abstract Object Store** in Python (FastAPI).
Work in progress.

## Installation

```bash
pip install -e git+https://github.com/cospectrum/boxdrive.git
```

## Quick Start

### Basic Usage

1. create `main.py`:
```python
from boxdrive import create_app
from boxdrive.stores import MemoryStore

store = MemoryStore()
app = create_app(store)
```

2. start API in dev mode:
```bash
fastapi dev main.py
```
The API will be available at `http://localhost:8000` with automatic documentation at `http://localhost:8000/docs`.

## API Endpoints

The API provides S3-compatible endpoints:

- `GET /` - List buckets
- `PUT /{bucket}` - Create a bucket
- `DELETE /{bucket}` - Delete a bucket
- `GET /{bucket}` - List objects in a bucket
- `GET /{bucket}/{key}` - Get an object
- `PUT /{bucket}/{key}` - Put an object
- `DELETE /{bucket}/{key}` - Delete an object

## Creating Custom Object Stores

To create a custom object store implementation, inherit from `ObjectStore`:

```python
import datetime
from collections.abc import AsyncIterator

from boxdrive import (
    BucketMetadata,
    ContentType,
    ETag,
    MaxKeys,
    Object,
    ObjectMetadata,
    ObjectStore,
)

class MyCustomStore(ObjectStore):
    async def list_buckets(self) -> list[BucketMetadata]: ...
    async def create_bucket(self, bucket_name: str) -> bool: ...
    async def delete_bucket(self, bucket_name: str) -> bool: ...
    async def list_objects(
        self, bucket_name: str, prefix: str | None = None, delimiter: str | None = None, max_keys: MaxKeys | None = None
    ) -> AsyncIterator[ObjectMetadata]:
        yield ObjectMetadata(
            key="", size=0, last_modified=datetime.datetime.now(datetime.UTC), etag="", content_type=""
        )
    async def get_object(self, bucket_name: str, key: str) -> Object | None: ...
    async def put_object(
        self, bucket_name: str, key: str, data: bytes, content_type: ContentType | None = None
    ) -> ETag: ...
    async def delete_object(self, bucket_name: str, key: str) -> bool: ...
    async def head_object(self, bucket_name: str, key: str) -> ObjectMetadata | None: ...
```

## Development

### Running Tests

unit:
```bash
uv run pytest/unit
```

e2e:
```bash
# start server
uv run fastapi dev src/boxdrive/main.py --port 8000
export S3_ENDPOINT_URL=http://127.0.0.1:8000

# run e2e tests
uv run run pytest/e2e
```

### Code Quality

```bash
uv run ruff format .
uv run ruff check . --fix
uv run mypy .
```

## License

Apache 2.0 - see [LICENSE](./LICENSE) file for details.
