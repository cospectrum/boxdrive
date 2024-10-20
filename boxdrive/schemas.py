from pydantic import BaseModel


class ListDir(BaseModel):
    path: str


class FileSaved(BaseModel):
    path: str
    length: int
