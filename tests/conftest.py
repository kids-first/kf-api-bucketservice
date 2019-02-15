import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_s3
from service import create_app, app


@pytest.yield_fixture(scope='session')
def client():
    app.config['TOKEN'] = ''
    app_context = app.app_context()
    app_context.push()

    yield app.test_client()


@pytest.yield_fixture
def logging_bucket():
    @mock_s3
    def f():
        s3 = boto3.client('s3')
        try:
            bucket = s3.create_bucket(
                    ACL='log-delivery-write',
                    Bucket=app.config['LOGGING_BUCKET'])
        except ClientError as e:
            pass

        try:
            dr_bucket = s3.create_bucket(
                    ACL='log-delivery-write',
                    Bucket=app.config['DR_LOGGING_BUCKET'],
                    CreateBucketConfiguration={'LocationConstraint': 'us-west-2'})
        except ClientError as e:
            pass
    yield f
