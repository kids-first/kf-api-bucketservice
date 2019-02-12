import boto3
import pytest
from service import create_app, app


@pytest.yield_fixture(scope='session')
def client():
    app.config['TOKEN'] = ''
    app_context = app.app_context()
    app_context.push()

    yield app.test_client()


@pytest.yield_fixture
def logging_bucket():
    def f():
        s3 = boto3.client('s3')
        bucket = s3.create_bucket(
                ACL='log-delivery-write',
                Bucket=app.config['LOGGING_BUCKET'])
        s3 = boto3.client('s3')
        dr_bucket = s3.create_bucket(
                ACL='log-delivery-write',
                Bucket=app.config['DR_LOGGING_BUCKET'],
                CreateBucketConfiguration={'LocationConstraint': 'us-west-2'})
    yield f
