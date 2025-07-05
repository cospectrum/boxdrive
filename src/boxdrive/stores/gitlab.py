import logging
import os
import urllib.parse
from typing import NoReturn

import httpx

from boxdrive.exceptions import BucketAlreadyExists
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
from boxdrive.store import ObjectStore

logger = logging.getLogger(__name__)


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
        self.repo_id = repo_id
        self.branch = branch
        self.api_url = api_url
        self.placeholder_name = placeholder_name
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {access_token}",
            },
        )

    async def list_buckets(self) -> list[BucketInfo]:
        """List all buckets in the store."""
        raise NotImplementedError

    def _raise_with_response(self, resp: httpx.Response) -> NoReturn:
        raise httpx.HTTPStatusError(
            f"gitlab error ({resp.status_code}): {resp.text}",
            request=resp.request,
            response=resp,
        )

    async def _file_exists(self, file_path: str) -> bool:
        """Return True if the file exists in the repository on the branch."""
        assert not file_path.startswith("/"), "file_path must not start with a slash"
        file_path = urllib.parse.quote_plus(file_path)
        file_url = os.path.join(self.api_url, "projects", str(self.repo_id), "repository/files", file_path)
        params = {"ref": self.branch}
        resp = await self.client.head(file_url, params=params)
        if resp.status_code == 200:
            return True
        if resp.status_code == 404:
            return False
        self._raise_with_response(resp)

    async def _object_exists(self, bucket_name: BucketName, key: Key) -> bool:
        """Return True if the object exists in the bucket on the branch."""
        file_path = f"{bucket_name}/{key}"
        return await self._file_exists(file_path)

    async def _bucket_exists(self, bucket_name: BucketName) -> bool:
        """Return True if any file exists under the bucket directory on the branch."""
        url = os.path.join(self.api_url, "projects", str(self.repo_id), "repository/tree")
        params = {"ref": self.branch, "path": bucket_name}
        resp = await self.client.get(url, params=params)
        if resp.status_code == 200:
            return True
        if resp.status_code == 404:
            return False
        self._raise_with_response(resp)

    async def create_bucket(self, bucket_name: BucketName) -> None:
        """Create a new bucket in the store by adding a placeholder file to the bucket directory."""
        file_path = f"{bucket_name}/{self.placeholder_name}"
        file_path = urllib.parse.quote_plus(file_path)
        file_url = os.path.join(self.api_url, "projects", str(self.repo_id), "repository/files", file_path)
        data = {
            "branch": self.branch,
            "content": "",
            "commit_message": f"create bucket {bucket_name}",
        }
        resp = await self.client.post(file_url, json=data)
        if resp.status_code == 201:
            return
        if resp.status_code == 400:
            logger.info("gitlab 400 response: %s", resp.text)
            raise BucketAlreadyExists
        self._raise_with_response(resp)

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
        raise NotImplementedError

    async def put_object(
        self, bucket_name: BucketName, key: Key, data: bytes, content_type: ContentType | None = None
    ) -> ObjectInfo:
        """Put an object into a bucket and return its info."""
        raise NotImplementedError

    async def delete_object(self, bucket_name: BucketName, key: Key) -> ObjectInfo:
        """Delete an object from a bucket and return its info."""
        raise NotImplementedError

    async def head_object(self, bucket_name: BucketName, key: Key) -> ObjectInfo:
        """Get object metadata without downloading the content."""
        raise NotImplementedError
