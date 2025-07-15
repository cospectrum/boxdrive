# BoxDrive
[![github]](https://github.com/cospectrum/boxdrive)
[![ci]](https://github.com/cospectrum/boxdrive/actions)

[github]: https://img.shields.io/badge/github-cospectrum/boxdrive-8da0cb?logo=github
[ci]: https://github.com/cospectrum/boxdrive/workflows/ci/badge.svg

S3-compatible API with **Abstract Object Store** in Python (FastAPI).
Work in progress.

## Built-in stores
- `InMemoryStore`
- `GitlabStore` (with some limitations)

## Quick Start

0. Install `boxdrive` from [PyPI](https://pypi.org/project/boxdrive/) using your preferred package manager:
```bash
uv add boxdrive
```

1. Create `main.py`:
```python
from boxdrive import create_app
from boxdrive.stores import InMemoryStore

store = InMemoryStore()
app = create_app(store)
```

2. Start the API (in development mode):
```bash
fastapi dev main.py
```
> By default, Swagger UI will be available at http://localhost:8000/docs

## API Endpoints

The API exposes the following S3-compatible endpoints:

- `GET /` - List buckets
- `PUT /{bucket}` - Create a bucket
- `DELETE /{bucket}` - Delete a bucket
- `GET /{bucket}` - List objects in a bucket
- `GET /{bucket}/{key}` - Get an object
- `PUT /{bucket}/{key}` - Put an object
- `DELETE /{bucket}/{key}` - Delete an object

## Creating Custom Object Stores

To use a custom object store, implement the `ObjectStore` interface and provide an instance to `create_app`:

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
    async def delete_object(self, bucket_name: BucketName, key: Key) -> None: ...
    async def head_object(self, bucket_name: BucketName, key: Key) -> ObjectInfo: ...
    async def list_objects(
        self,
        bucket_name: BucketName,
        *,
        prefix: Key | None = None,
        delimiter: str | None = None,
        max_keys: MaxKeys = 1000,
        marker: Key | None = None,
        encoding_type: str | None = None,
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

### API

0. Start the monitoring pipeline:
```sh
docker compose -f docker-compose-monitoring.yaml up --detach --wait
```
> Telemetry data will be saved in ClickHouse, which is exposed at localhost:8123.

1. Start the API:
```sh
export OTEL_EXPORTER_HTTP_ENDPOINT=http://localhost:4318
uv run fastapi dev examples/inmemory.py
```

### Tests

#### Unit tests
```bash
uv run pytest tests/unit
```

#### End-to-end (e2e) tests  
The API should be running in the background.
```bash
export S3_ENDPOINT_URL=http://127.0.0.1:8000
uv run run pytest tests/e2e
```

#### Third-party S3 tests  
The API should be running in the background.
```bash
cd tests/third_party/s3-tests
export S3TEST_CONF=s3tests.conf
uv run tox -- s3tests_boto3/functional/test_s3.py -m boxdrive
```
See [tests/third_party/s3-tests/boxdrive.md](./tests/third_party/s3-tests/boxdrive.md)
for additional information.

### Code Quality

```bash
uv run ruff format .
uv run ruff check . --fix
uv run mypy .
```

## License

Apache 2.0 – see the [LICENSE](./LICENSE) file for details.

