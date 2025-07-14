import json
import logging
import os
import urllib.parse
from typing import Literal, NoReturn

import httpx
from pydantic import BaseModel, PositiveInt

logger = logging.getLogger(__name__)


class FileHead(BaseModel):
    gitlab_size: int
    gitlab_content_sha256: str


class DeleteFile(BaseModel):
    branch: str
    commit_message: str = ""
    author_name: str | None = None
    author_email: str | None = None


class UpdateFile(DeleteFile):
    content: str = ""
    encoding: Literal["text", "base64"] | None = None


class CreateFile(UpdateFile):
    pass


class TreeParams(BaseModel):
    ref: str
    path: str | None = None
    recursive: bool | None = None
    page: PositiveInt | None = None
    per_page: PositiveInt | None = None
    pagination: Literal["keyset", "legacy"] | None = None


class TreeItem(BaseModel):
    id: str
    name: str
    type: Literal["blob", "tree"]
    path: str


class TreeHeaders(BaseModel):
    total: int
    total_pages: int


class Tree(BaseModel):
    items: list[TreeItem]
    headers: TreeHeaders


class GitlabClient:
    def __init__(
        self,
        repo_id: int,
        access_token: str,
        api_url: str = "https://gitlab.com/api/v4/",
        timeout: float | None = None,
    ):
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {access_token}",
            },
        )
        self.repo_id = repo_id
        self.api_url = api_url

    async def create_file(self, file_path: str, body: CreateFile) -> httpx.Response:
        file_path = urllib.parse.quote_plus(file_path)
        file_url = os.path.join(self.api_url, "projects", str(self.repo_id), "repository/files", file_path)
        data = body.model_dump(exclude_none=True)
        return await self.client.post(file_url, json=data)

    async def update_file(self, file_path: str, body: UpdateFile) -> httpx.Response:
        file_path = urllib.parse.quote_plus(file_path)
        file_url = os.path.join(self.api_url, "projects", str(self.repo_id), "repository/files", file_path)
        data = body.model_dump(exclude_none=True)
        return await self.client.put(file_url, json=data)

    async def delete_file(self, file_path: str, params: DeleteFile) -> httpx.Response:
        file_path = urllib.parse.quote_plus(file_path)
        file_url = os.path.join(self.api_url, "projects", str(self.repo_id), "repository/files", file_path)
        return await self.client.delete(file_url, params=params.model_dump(exclude_none=True))

    async def get_raw_file(self, file_path: str, *, ref: str) -> httpx.Response:
        file_path = urllib.parse.quote_plus(file_path)
        file_url = os.path.join(self.api_url, "projects", str(self.repo_id), "repository/files", file_path)
        file_url = os.path.join(file_url, "raw")
        params = {
            "ref": ref,
        }
        return await self.client.get(file_url, params=params)

    async def head_file(self, file_path: str, *, ref: str) -> FileHead | None:
        file_path = urllib.parse.quote_plus(file_path)
        file_url = os.path.join(self.api_url, "projects", str(self.repo_id), "repository/files", file_path)
        params = {
            "ref": ref,
        }
        resp = await self.client.head(file_url, params=params)
        if resp.status_code == 404:
            return None
        if resp.status_code == 200:
            return FileHead(
                gitlab_content_sha256=resp.headers["x-gitlab-content-sha256"],
                gitlab_size=int(resp.headers["x-gitlab-size"]),
            )
        raise_for_gitlab_response(resp)

    async def get_tree(self, params: TreeParams) -> Tree:
        tree_url = os.path.join(self.api_url, "projects", str(self.repo_id), "repository/tree")
        resp = await self.client.get(tree_url, params=params.model_dump(exclude_none=True))
        if resp.status_code == 200:
            items = json.loads(resp.content)
            headers = TreeHeaders(
                total=int(resp.headers["x-total"]),
                total_pages=int(resp.headers["x-total-pages"]),
            )
            return Tree(items=items, headers=headers)
        raise_for_gitlab_response(resp)


def raise_for_gitlab_response(resp: httpx.Response) -> NoReturn:
    raise httpx.HTTPStatusError(
        f"gitlab error ({resp.status_code}): {resp.text}",
        request=resp.request,
        response=resp,
    )
