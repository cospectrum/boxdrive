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


class OwnerXml(BaseXmlModel, tag="Owner"):
    ID: str = element(tag="ID")
    DisplayName: str = element(tag="DisplayName")


class BucketXml(BaseXmlModel, tag="Bucket"):
    Name: str = element(tag="Name")
    CreationDate: str = element(tag="CreationDate")


class BucketsXml(BaseXmlModel, tag="Buckets"):
    Bucket: list[BucketXml] = element(tag="Bucket")


class ListAllMyBucketsResultXml(BaseXmlModel, tag="ListAllMyBucketsResult"):
    xmlns: str = attr(default=constants.S3_XML_NAMESPACE)
    Owner: OwnerXml = element(tag="Owner")
    Buckets: BucketsXml = element(tag="Buckets")


class OwnerShortXml(BaseXmlModel, tag="Owner"):
    ID: str = element(tag="ID")
    DisplayName: str = element(tag="DisplayName")


class ContentsXml(BaseXmlModel, tag="Contents"):
    Key: str = element(tag="Key")
    LastModified: str = element(tag="LastModified")
    ETag: str = element(tag="ETag")
    Size: int = element(tag="Size")
    StorageClass: str = element(tag="StorageClass")
    Owner: OwnerShortXml = element(tag="Owner")


class ListBucketResultXml(BaseXmlModel, tag="ListBucketResult"):
    xmlns: str = attr(default=constants.S3_XML_NAMESPACE)
    Name: str = element(tag="Name")
    Prefix: str = element(tag="Prefix")
    MaxKeys: int = element(tag="MaxKeys")
    IsTruncated: str = element(tag="IsTruncated")
    Delimiter: str | None = element(tag="Delimiter", default=None)
    Contents: list[ContentsXml] = element(tag="Contents")
