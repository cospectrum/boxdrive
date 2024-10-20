import uuid
import os

from fastapi import UploadFile


def filename(file: UploadFile) -> str:
    if file.filename is None:
        return uuid4()
    return file.filename


def uuid4() -> str:
    return str(uuid.uuid4())


def mkdir(path: str) -> None:
    if os.path.exists(path):
        return
    os.makedirs(path)
