# BoxDrive
[![github]](https://github.com/cospectrum/boxdrive)
[![ci]](https://github.com/cospectrum/boxdrive/actions)

[github]: https://img.shields.io/badge/github-cospectrum/boxdrive-8da0cb?logo=github
[ci]: https://github.com/cospectrum/boxdrive/workflows/ci/badge.svg

S3-compatible API with **Abstract Object Store** in Python (FastAPI).
Work in progress.

## Installation

```bash
uv add boxdrive
```

## Quick Start

### Basic Usage

1. create `main.py`:
```python
from boxdrive import create_app
from boxdrive.stores import InMemoryStore

store = InMemoryStore()
app = create_app(store)
```

2. start API (in dev mode):
```bash
fastapi dev main.py
```
> Swagger will start on http://localhost:8000/docs by default

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
from boxdrive import (
    BucketInfo,
    BucketName,
    ContentType,
    Key,
    ListObjectsInfo,
    ListObjectsV2Info,
    MaxKeys,
    Object,
    ObjectInfo,
    ObjectStore,
)

class MyCustomStore(ObjectStore):
    async def list_buckets(self) -> list[BucketInfo]: ...
    async def create_bucket(self, bucket_name: BucketName) -> None: ...
    async def delete_bucket(self, bucket_name: BucketName) -> None: ...
    async def get_object(self, bucket_name: BucketName, key: Key) -> Object: ...
    async def put_object(
        self, bucket_name: BucketName, key: Key, data: bytes, content_type: ContentType | None = None
    ) -> ObjectInfo: ...
    async def delete_object(self, bucket_name: BucketName, key: Key) -> ObjectInfo: ...
    async def head_object(self, bucket_name: BucketName, key: Key) -> ObjectInfo: ...
    async def list_objects(
        self,
        bucket_name: BucketName,
        *,
        prefix: Key | None = None,
        delimiter: str | None = None,
        max_keys: MaxKeys = 1000,
        marker: Key | None = None,
    ) -> ListObjectsInfo: ...
    async def list_objects_v2(
        self,
        bucket_name: BucketName,
        *,
        continuation_token: Key | None = None,
        delimiter: str | None = None,
        encoding_type: str | None = None,
        max_keys: MaxKeys = 1000,
        prefix: Key | None = None,
        start_after: Key | None = None,
    ) -> ListObjectsV2Info: ...
```
> Use exceptions from [boxdrive.exceptions](./src/boxdrive/exceptions.py)
> (e.g., NoSuchBucket, NoSuchKey) in your custom store implementation.

## Development

### Tests

#### unit
```bash
uv run pytest tests/unit
```

#### e2e
API should run in the background.
```bash
export S3_ENDPOINT_URL=http://127.0.0.1:8000
uv run run pytest tests/e2e
```

#### third_party/s3-tests
API should run in the background.
```bash
cd tests/third_party/s3-tests
export S3TEST_CONF=s3tests.conf
uv run tox -- s3tests_boto3/functional/test_s3.py -m boxdrive
```
See [tests/third_party/s3-tests/boxdrive.md](./tests/third_party/s3-tests/boxdrive.md)
for additional info.

### Code Quality

```bash
uv run ruff format .
uv run ruff check . --fix
uv run mypy .
```

## License

Apache 2.0 - see [LICENSE](./LICENSE) file for details.
