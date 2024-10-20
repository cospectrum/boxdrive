from pydantic import BaseModel


class ListDir(BaseModel):
    path: str
