# s3-tests

API should run in the background.

Point to your test configuration:
```sh
export S3TEST_CONF=s3tests.conf
```

Run all tests marked for inmemory:
```sh
uv run tox -- s3tests_boto3/functional/test_s3.py -m inmemory
```

Run specific test:
```sh
uv run tox -- s3tests_boto3/functional/test_s3.py::test_basic_key_count
```
