# s3-tests

Run all tests marked for boxdrive:
```sh
S3TEST_CONF=s3tests.conf tox -- s3tests_boto3/functional/test_s3.py -m boxdrive
```

Run specific test:
```sh
S3TEST_CONF=s3tests.conf tox -- s3tests_boto3/functional/test_s3.py::test_basic_key_count
```
