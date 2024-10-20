import uvicorn

from .app import app


def main() -> None:
    host = "0.0.0.0"
    port = 8000
    timeout_keep_alive = 0

    uvicorn.run(
        app,
        host=host,
        port=port,
        timeout_keep_alive=timeout_keep_alive,
    )
