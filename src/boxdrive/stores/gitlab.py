import base64
import datetime
import hashlib
import logging
import os
import urllib.parse
from typing import Literal, NoReturn

import httpx
from pydantic import BaseModel, PositiveInt

from boxdrive import constants, exceptions
from boxdrive.schemas import (
    BucketInfo,
    BucketName,
    ContentType,
    Key,
    ListObjectsInfo,
    ListObjectsV2Info,
    MaxKeys,
    Object,
    ObjectInfo,
)
from boxdrive.schemas.store import validate_bucket_name
from boxdrive.store import ObjectStore

logger = logging.getLogger(__name__)


class File(BaseModel):
    content: str


class DeleteFile(BaseModel):
    ref: str
    commit_message: str = ""
    author_name: str | None = None
    author_email: str | None = None


class CreateFile(DeleteFile):
    content: str = ""
    encoding: Literal["text", "base64"] | None = None


class TreeParams(BaseModel):
    ref: str
    path: str | None = None
    recursive: bool | None = None
    page: PositiveInt | None = None
    per_page: PositiveInt | None = None
    pagination: Literal["keyset", "legacy"] | None = None


class TreeItem(BaseModel):
    name: str
    type: Literal["blob", "tree"]
    path: str


class Tree(BaseModel):
    items: list[TreeItem]


class GitlabClient:
    def __init__(
        self,
        repo_id: int,
        access_token: str,
        api_url: str = "https://gitlab.com/api/v4/",
    ):
        self.client = httpx.AsyncClient(
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

    async def delete_file(self, file_path: str, params: DeleteFile) -> httpx.Response:
        file_path = urllib.parse.quote_plus(file_path)
        file_url = os.path.join(self.api_url, "projects", str(self.repo_id), "repository/files", file_path)
        return await self.client.delete(file_url, params=params.model_dump(exclude_none=True))

    async def get_file(self, file_path: str, *, ref: str) -> httpx.Response:
        file_path = urllib.parse.quote_plus(file_path)
        file_url = os.path.join(self.api_url, "projects", str(self.repo_id), "repository/files", file_path)
        params = {
            "ref": ref,
        }
        return await self.client.get(file_url, params=params)

    async def get_tree(self, params: TreeParams) -> list[TreeItem]:
        tree_url = os.path.join(self.api_url, "projects", str(self.repo_id), "repository/tree")
        resp = await self.client.get(tree_url, params=params.model_dump(exclude_none=True))
        if resp.status_code == 200:
            tree = Tree.model_validate_json(resp.content)
            return tree.items
        _raise_for_gitlab_response(resp)


def _raise_for_gitlab_response(resp: httpx.Response) -> NoReturn:
    raise httpx.HTTPStatusError(
        f"gitlab error ({resp.status_code}): {resp.text}",
        request=resp.request,
        response=resp,
    )


class GitlabStore(ObjectStore):
    """Object store implementation backed by a GitLab repository branch via the GitLab API."""

    def __init__(
        self,
        repo_id: int,
        branch: str,
        *,
        access_token: str,
        api_url: str = "https://gitlab.com/api/v4/",
        placeholder_name: str = ".gitkeep",
    ):
        """Initialize the GitLab store with repository, token, branch, and placeholder file name."""
        self.gitlab_client = GitlabClient(repo_id, access_token, api_url)
        self.branch = branch
        self.placeholder_name = placeholder_name

    def _file_path(self, bucket_name: BucketName, key: Key, allow_placeholder: bool = False) -> str:
        validate_bucket_name(bucket_name)
        if key == self.placeholder_name and not allow_placeholder:
            raise exceptions.NoSuchKey
        return f"{bucket_name}/{key}"

    async def list_buckets(self) -> list[BucketInfo]:
        """List all buckets in the store."""
        tree = await self.gitlab_client.get_tree(TreeParams(ref=self.branch))
        buckets = [
            BucketInfo(name=item.name, creation_date=datetime.datetime.now(datetime.UTC))
            for item in tree
            if item.type == "tree"
        ]
        return buckets

    async def create_bucket(self, bucket_name: BucketName) -> None:
        """Create a new bucket in the store by adding a placeholder file to the bucket directory."""
        file_path = self._file_path(bucket_name, self.placeholder_name, allow_placeholder=True)
        body = CreateFile(
            ref=self.branch,
            commit_message=f"create bucket {bucket_name}",
        )
        resp = await self.gitlab_client.create_file(file_path, body)
        if resp.status_code == 201:
            return
        if resp.status_code == 400:
            logger.info("gitlab response (400): %s", resp.text)
            raise exceptions.BucketAlreadyExists
        _raise_for_gitlab_response(resp)

    async def delete_bucket(self, bucket_name: BucketName) -> None:
        """Delete a bucket from the store."""
        raise NotImplementedError

    async def list_objects(
        self,
        bucket_name: BucketName,
        *,
        prefix: Key | None = None,
        delimiter: str | None = None,
        max_keys: MaxKeys = 1000,
        marker: Key | None = None,
    ) -> ListObjectsInfo:
        """List objects in a bucket."""
        raise NotImplementedError

    async def list_objects_v2(
        self,
        bucket_name: BucketName,
        *,
        continuation_token: Key | None = None,
        delimiter: str | None = None,
        encoding_type: str | None = None,
        max_keys: MaxKeys = 1000,
        prefix: Key | None = None,
        start_after: Key | None = None,
    ) -> ListObjectsV2Info:
        """List objects in a bucket."""
        raise NotImplementedError

    async def get_object(self, bucket_name: BucketName, key: Key) -> Object:
        """Get an object by bucket and key."""
        file_path = self._file_path(bucket_name, key)
        resp = await self.gitlab_client.get_file(file_path, ref=self.branch)
        if resp.status_code == 200:
            body = File.model_validate_json(resp.content)
            data = base64.b64decode(body.content)
            return Object(
                data=data,
                info=ObjectInfo(
                    key=key,
                    size=len(data),
                    last_modified=datetime.datetime.now(datetime.UTC),
                    etag=hashlib.md5(data).hexdigest(),
                    content_type=constants.DEFAULT_CONTENT_TYPE,
                ),
            )
        if resp.status_code == 404:
            raise exceptions.NoSuchKey
        _raise_for_gitlab_response(resp)

    async def put_object(
        self, bucket_name: BucketName, key: Key, data: bytes, content_type: ContentType | None = None
    ) -> ObjectInfo:
        file_path = self._file_path(bucket_name, key)
        content = base64.b64encode(data).decode("utf-8")
        body = CreateFile(
            ref=self.branch,
            commit_message=f"put object {bucket_name}/{key}",
            content=content,
        )
        resp = await self.gitlab_client.create_file(file_path, body)
        if resp.status_code == 201:
            return ObjectInfo(
                key=key,
                size=len(data),
                last_modified=datetime.datetime.now(datetime.UTC),
                etag=hashlib.md5(data).hexdigest(),
                content_type=constants.DEFAULT_CONTENT_TYPE,
            )
        _raise_for_gitlab_response(resp)

    async def delete_object(self, bucket_name: BucketName, key: Key) -> None:
        """Delete an object from a bucket."""
        file_path = self._file_path(bucket_name, key, allow_placeholder=True)
        params = DeleteFile(
            ref=self.branch,
            commit_message=f"delete object {bucket_name}/{key}",
        )
        resp = await self.gitlab_client.delete_file(file_path, params)
        if resp.status_code == 204:
            return
        if resp.status_code == 400:
            logger.info("gitlab response (400): %s", resp.text)
            return
        _raise_for_gitlab_response(resp)

    async def head_object(self, bucket_name: BucketName, key: Key) -> ObjectInfo:
        obj = await self.get_object(bucket_name, key)
        return obj.info
