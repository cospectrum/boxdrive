import os
from pathlib import Path
from fastapi import APIRouter, UploadFile

from boxdrive import common

from .schemas import ListDir, FileSaved
from .const import root


router = APIRouter()


@router.post("/listdir/")
def listdir(req: ListDir) -> list[str]:
    path = Path(root) / req.path
    return os.listdir(path)


@router.post("/uploadfile/")
async def upload_file(file: UploadFile) -> FileSaved:
    save_path = Path(root) / (file.filename or common.uuid4())
    with open(save_path, "wb") as f:
        content = await file.read()
        length = f.write(content)
    return FileSaved(path=str(save_path), length=length)
