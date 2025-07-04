import urllib.parse

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


class GitlabStore(ObjectStore):
    """Object store implementation backed by a GitLab repository branch via the GitLab API."""

    def __init__(
        self,
        repo_id: str,
        token: str,
        branch: str,
        api_url: str = "https://gitlab.com/api/v4",
        placeholder_name: str = ".gitkeep",
    ):
        """Initialize the GitLab store with repository, token, branch, and placeholder file name."""
        self.repo_id = repo_id
        self.token = token
        self.branch = branch
        self.api_url = api_url
        self.placeholder_name = placeholder_name
        self.client = httpx.AsyncClient(headers={"PRIVATE-TOKEN": token})

    async def list_buckets(self) -> list[BucketInfo]:
        """List all buckets in the store."""
        raise NotImplementedError

    async def _bucket_exists(self, bucket_name: BucketName) -> bool:
        """Return True if any file exists under the bucket directory on the branch."""
        tree_url = f"{self.api_url}/projects/{self.repo_id}/repository/tree"
        params = {"path": bucket_name, "ref": self.branch}
        resp = await self.client.get(tree_url, params=params)
        resp.raise_for_status()
        return bool(resp.json())

    async def _object_exists(self, bucket_name: BucketName, key: Key) -> bool:
        """Return True if the object exists in the bucket on the branch."""
        file_path = f"{bucket_name}/{key}"
        file_url = f"{self.api_url}/projects/{self.repo_id}/repository/files/{urllib.parse.quote(file_path, safe='')}"
        params = {"ref": self.branch}
        resp = await self.client.get(file_url, params=params)
        if resp.status_code == 200:
            return True
        if resp.status_code == 404:
            return False
        resp.raise_for_status()
        return False

    async def create_bucket(self, bucket_name: BucketName) -> None:
        """Create a new bucket in the store by adding a placeholder file to the bucket directory."""
        if await self._bucket_exists(bucket_name):
            raise BucketAlreadyExists
        file_path = f"{bucket_name}/{self.placeholder_name}"
        file_url = f"{self.api_url}/projects/{self.repo_id}/repository/files/{urllib.parse.quote(file_path, safe='')}"
        data = {
            "branch": self.branch,
            "content": "placeholder",
            "commit_message": f"Create bucket {bucket_name} with placeholder",
        }
        put_resp = await self.client.post(file_url, json=data)
        if put_resp.status_code != 201:
            raise RuntimeError(f"Failed to create bucket: {put_resp.text}")

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
