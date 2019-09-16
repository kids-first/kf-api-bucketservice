import boto3
import datetime
import json
import jwt
import pytest
from botocore.exceptions import ClientError
from moto import mock_s3
from unittest.mock import patch
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


@pytest.yield_fixture(autouse=True)
def auth0_key_mock():
    """
    Mocks out the response from the /.well-known/jwks.json endpoint on auth0
    """

    class MockResp:
        def json(self):
            with open("tests/jwks.json", "r") as f:
                return json.load(f)

    with patch(f"service.requests.get") as get:
        get.return_value = MockResp()
        yield get


@pytest.fixture()
def service_token():
    """
    Generate a service token that will be used in machine-to-machine auth
    """
    with open("tests/private_key.pem", "rb") as f:
        key = f.read()

    def make_token(gty="client-credentials"):
        now = datetime.datetime.now()
        tomorrow = now + datetime.timedelta(days=1)
        token = {
            "iss": "auth0.com",
            "sub": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@clients",
            "aud": "https://kf-study-creator.kidsfirstdrc.org",
            "iat": now.timestamp(),
            "exp": tomorrow.timestamp(),
            "azp": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "scope": "admin",
            "gty": gty,
        }
        return jwt.encode(token, key, algorithm="RS256").decode("utf8")

    return make_token


@pytest.yield_fixture()
def service_client(client, service_token):
    client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {service_token()}"
    yield client
