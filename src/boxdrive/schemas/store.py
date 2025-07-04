"""Schema definitions and validated types for BoxDrive API."""

import datetime
import re
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field


def validate_bucket_name(value: str) -> str:
    """Validate S3 bucket name according to AWS rules."""
    in_range = 3 <= len(value) <= 63
    if not in_range:
        raise ValueError("Bucket name must be between 3 and 63 characters")

    if not re.match(r"^[a-z0-9][a-z0-9.-]*[a-z0-9]$", value):
        raise ValueError(
            "Bucket name must contain only lowercase letters, numbers, dots, and hyphens, and must start and end with a letter or number"
        )

    if value.startswith(".") or value.endswith("."):
        raise ValueError("Bucket name cannot start or end with a dot")

    if ".." in value:
        raise ValueError("Bucket name cannot contain consecutive dots")

    if re.match(r"^\d+\.\d+\.\d+\.\d+$", value):
        raise ValueError("Bucket name cannot be formatted as an IP address")

    return value


def validate_key(value: str) -> str:
    """Validate S3 object key."""
    if len(value) == 0:
        raise ValueError("Key cannot be empty")

    if len(value) > 1024:
        raise ValueError("Key cannot be longer than 1024 characters")

    # Check for invalid characters
    if "\0" in value:
        raise ValueError("Key cannot contain null characters")

    return value


def validate_etag(value: str) -> str:
    """Validate ETag format."""
    # ETags are typically MD5 hashes (32 hex characters) optionally wrapped in quotes
    if not re.match(r'^"?[a-fA-F0-9]{32}"?$', value):
        raise ValueError("ETag must be a 32-character hexadecimal string, optionally wrapped in quotes")

    return value


def validate_content_type(value: str) -> str:
    """Validate content type format."""
    # Basic MIME type validation
    if not re.match(
        r"^[a-zA-Z0-9!#$&\-\^_]*/[a-zA-Z0-9!#$&\-\^_]*(\s*;\s*[a-zA-Z0-9!#$&\-\^_]*=[a-zA-Z0-9!#$&\-\^_]*)*$", value
    ):
        raise ValueError("Invalid content type format")

    return value


def validate_max_keys(value: int) -> int:
    """Validate max_keys parameter."""
    in_range = 1 <= value <= 1000
    if not in_range:
        raise ValueError("max_keys must be between 1 and 1000")
    return value


BucketName = Annotated[str, AfterValidator(validate_bucket_name)]
Key = Annotated[str, AfterValidator(validate_key)]
ETag = Annotated[str, AfterValidator(validate_etag)]
ContentType = Annotated[str, AfterValidator(validate_content_type)]
MaxKeys = Annotated[int, AfterValidator(validate_max_keys)]


class BucketInfo(BaseModel):
    """info for a bucket in the store."""

    name: BucketName
    creation_date: datetime.datetime


class ObjectInfo(BaseModel):
    """info for an object in the store."""

    key: Key
    size: int
    last_modified: datetime.datetime
    etag: ETag
    content_type: ContentType


class Object(BaseModel):
    """Represents an object with its data and info."""

    data: bytes
    info: ObjectInfo


class ListObjectsInfo(BaseModel):
    objects: list[ObjectInfo]
    is_truncated: bool
    common_prefixes: list[str] = Field(default_factory=list)


class ListObjectsV2Info(ListObjectsInfo):
    pass
