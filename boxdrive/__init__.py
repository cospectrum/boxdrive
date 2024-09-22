import uvicorn

from fastapi import FastAPI


app = FastAPI()


def main() -> None:
    host = '0.0.0.0'
    uvicorn.run(app, host=host)
