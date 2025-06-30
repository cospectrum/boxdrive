# BoxDrive

A generic object store with S3-compatible API built with FastAPI.

## Features

- **S3-compatible API**: Supports standard S3 operations (GET, PUT, DELETE, HEAD, LIST)
- **Abstract Object Store**: Pluggable storage backends through the `ObjectStore` interface
- **FastAPI-based**: Modern, fast web framework with automatic API documentation
- **Async-first**: Built with async/await for high performance
- **Type-safe**: Full type hints and mypy support

## Installation

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

## Quick Start

### Basic Usage

```python
import asyncio
import uvicorn
from boxdrive import create_app, MemoryStore

async def main():
    # Create an in-memory store
    store = MemoryStore()
    
    # Create the FastAPI app
    app = create_app(store)
    
    # Run the server
    config = uvicorn.Config(app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
```

### Running the Example

```bash
python examples/basic_usage.py
```

The API will be available at `http://localhost:8000` with automatic documentation at `http://localhost:8000/docs`.

## API Endpoints

The API provides S3-compatible endpoints:

- `GET /{bucket}` - List objects in a bucket
- `GET /{bucket}/{key}` - Get an object
- `PUT /{bucket}/{key}` - Put an object
- `DELETE /{bucket}/{key}` - Delete an object
- `HEAD /{bucket}/{key}` - Get object metadata
- `POST /{bucket}` - Create a bucket
- `DELETE /{bucket}` - Delete a bucket

## Creating Custom Object Stores

To create a custom object store implementation, inherit from `ObjectStore`:

```python
from boxdrive import ObjectStore, ObjectMetadata
from typing import AsyncIterator, Optional

class MyCustomStore(ObjectStore):
    async def list_objects(self, prefix=None, delimiter=None, max_keys=None):
        # Implement object listing
        pass
    
    async def get_object(self, key: str) -> Optional[bytes]:
        # Implement object retrieval
        pass
    
    async def put_object(self, key: str, data: bytes, content_type=None) -> str:
        # Implement object storage
        pass
    
    # ... implement other required methods
```

## Development

### Running Tests

```bash
# Using uv
uv run pytest

# Or using pytest directly
pytest
```

### Code Quality

```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Type checking
uv run mypy src/
```

## License

MIT License - see LICENSE file for details.
