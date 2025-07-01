from typing import Any

from fastapi.responses import Response
from pydantic_xml import BaseXmlModel, attr, element

from boxdrive import constants


class XMLResponse(Response):
    media_type = "application/xml"

    def render(self, content: Any) -> bytes:
        match content:
            case None:
                return b""
            case BaseXmlModel():
                xml = content.to_xml()
                if isinstance(xml, str):
                    return xml.encode(self.charset)
                assert isinstance(xml, bytes), f"Expected bytes, got {type(xml)}"
                return xml
            case _:
                raise ValueError(f"Expected None or BaseXmlModel, got {type(content)}")


class Owner(BaseXmlModel):
    id: str = element(tag="ID")
    display_name: str = element(tag="DisplayName")


class Bucket(BaseXmlModel):
    name: str = element(tag="Name")
    creation_date: str = element(tag="CreationDate")


class Buckets(BaseXmlModel):
    buckets: list[Bucket] = element(tag="Bucket")


class ListAllMyBucketsResult(BaseXmlModel):
    xmlns: str = attr(default=constants.S3_XML_NAMESPACE)
    owner: Owner = element(tag="Owner")
    buckets: Buckets = element(tag="Buckets")


class Content(BaseXmlModel):
    key: str = element(tag="Key")
    last_modified: str = element(tag="LastModified")
    etag: str = element(tag="ETag")
    size: int = element(tag="Size")
    storage_class: str = element(tag="StorageClass")
    owner: Owner = element(tag="Owner")


class CommonPrefix(BaseXmlModel):
    prefix: str = element(tag="Prefix")


class ListBucketResult(BaseXmlModel):
    xmlns: str = attr(default=constants.S3_XML_NAMESPACE)
    name: str = element(tag="Name")
    prefix: str = element(tag="Prefix")
    max_keys: int = element(tag="MaxKeys")
    key_count: int = element(tag="KeyCount")
    is_truncated: bool = element(tag="IsTruncated")
    delimiter: str | None = element(tag="Delimiter", default=None)
    contents: list[Content] = element(tag="Contents")
    common_prefixes: list[CommonPrefix] = element(tag="CommonPrefixes")
