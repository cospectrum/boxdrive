import urllib.parse

from boxdrive.schemas import Key, ListObjectsInfo, ListObjectsV2Info, MaxKeys, ObjectInfo


def _encode_keys_and_prefixes(
    objects: list[ObjectInfo],
    common_prefixes: list[str],
    *,
    encoding_type: str | None = None,
) -> tuple[list[ObjectInfo], list[str]]:
    if encoding_type == "url":
        objects = [obj.model_copy(update={"key": urllib.parse.quote(obj.key)}) for obj in objects]
        common_prefixes = [urllib.parse.quote(prefix) for prefix in common_prefixes]
    return objects, common_prefixes


def filter_objects(
    objects: list[ObjectInfo],
    *,
    prefix: Key | None = None,
    delimiter: str | None = None,
    max_keys: MaxKeys = 1000,
    marker: Key | None = None,
    encoding_type: str | None = None,
) -> ListObjectsInfo:
    if prefix:
        objects = [obj for obj in objects if obj.key.startswith(prefix)]

    objects = sorted(objects, key=lambda obj: obj.key)
    if marker:
        objects = [obj for obj in objects if obj.key > marker]

    is_truncated = len(objects) > max_keys
    objects = objects[:max_keys]

    objects, common_prefixes = _split_contents_and_prefixes(objects, prefix=prefix, delimiter=delimiter)
    objects, common_prefixes = _encode_keys_and_prefixes(objects, common_prefixes, encoding_type=encoding_type)
    return ListObjectsInfo(
        is_truncated=is_truncated,
        common_prefixes=common_prefixes,
        objects=objects,
    )


def filter_objects_v2(
    objects: list[ObjectInfo],
    *,
    continuation_token: Key | None = None,
    delimiter: str | None = None,
    encoding_type: str | None = None,
    max_keys: MaxKeys = 1000,
    prefix: Key | None = None,
    start_after: Key | None = None,
) -> ListObjectsV2Info:
    if prefix:
        objects = [obj for obj in objects if obj.key.startswith(prefix)]
    objects = sorted(objects, key=lambda obj: obj.key)

    after = continuation_token or start_after
    if after:
        objects = [obj for obj in objects if obj.key > after]

    is_truncated = len(objects) > max_keys
    objects = objects[:max_keys]

    objects, common_prefixes = _split_contents_and_prefixes(objects, prefix=prefix, delimiter=delimiter)
    objects, common_prefixes = _encode_keys_and_prefixes(objects, common_prefixes, encoding_type=encoding_type)
    return ListObjectsV2Info(objects=objects, is_truncated=is_truncated, common_prefixes=common_prefixes)


def _split_contents_and_prefixes(
    objects: list[ObjectInfo], *, prefix: Key | None, delimiter: str | None
) -> tuple[list[ObjectInfo], list[str]]:
    prefix = prefix or ""
    if not delimiter:
        return objects, []
    contents = []
    common_prefixes = set()
    plen = len(prefix)
    for obj in objects:
        assert obj.key.startswith(prefix), "all objects must be filtered by prefix before splitting"
        key = obj.key[plen:]
        if delimiter in key:
            idx = key.index(delimiter)
            common_prefix = obj.key[: plen + idx + len(delimiter)]
            common_prefixes.add(common_prefix)
        else:
            contents.append(obj)
    return contents, sorted(common_prefixes)
