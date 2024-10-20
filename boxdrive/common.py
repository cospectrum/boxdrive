import uuid
import os


def uuid4() -> str:
    return str(uuid.uuid4())


def mkdir(path: str) -> None:
    if os.path.exists(path):
        return
    os.makedirs(path)
