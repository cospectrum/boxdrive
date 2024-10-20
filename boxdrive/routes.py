import os
from fastapi import APIRouter, UploadFile

from .schemas import ListDir
from .common import filename
from .const import root


router = APIRouter()


@router.post("/listdir/")
def listdir(req: ListDir) -> list[str]:
    path = os.path.join(root, req.path)
    return os.listdir(path)


@router.post("/uploadfile/")
async def upload_file(file: UploadFile) -> dict[str, str]:
    file_name = filename(file)
    save_path = os.path.join(root, file_name)
    with open(save_path, 'wb') as f:
        content = await file.read()
        f.write(content)
    return dict(file_name=file_name)
