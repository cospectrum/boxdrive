import uvicorn

from .app import app


def main() -> None:
    host = '0.0.0.0'
    port = 80
    timeout_keep_alive = 0
    reload = True

    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
        timeout_keep_alive=timeout_keep_alive,
    )
