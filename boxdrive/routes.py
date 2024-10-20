import os
from pathlib import Path
from fastapi import APIRouter, UploadFile

from .schemas import ListDir
from .common import filename
from .const import root


router = APIRouter()


@router.post("/listdir/")
def listdir(req: ListDir) -> list[str]:
    path = Path(root) / req.path
    return os.listdir(path)


@router.post("/uploadfile/")
async def upload_file(file: UploadFile) -> dict[str, Path]:
    save_path = Path(root) / filename(file)
    with open(save_path, "wb") as f:
        content = await file.read()
        f.write(content)
    return dict(save_path=save_path)
