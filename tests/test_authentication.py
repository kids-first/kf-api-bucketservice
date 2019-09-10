import boto3
import json
import jwt
import pytest
import datetime
from flask import url_for
from service import app
from unittest.mock import patch
from moto import mock_s3


@pytest.fixture(scope="module")
def auth0_key_mock():
    """
    Mocks out the response from the /.well-known/jwks.json endpoint on auth0
    """

    class MockResp:
        @property
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


@mock_s3
def test_get_key(auth0_key_mock):
    app.config["TOKEN"] = "abc123"
    app.config["AUTH0_JWKS"] = "https://auth0/jwks.json"
    app_context = app.app_context()
    app_context.push()
    client = app.test_client()

    resp = client.post(
        "/buckets",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"study_id": "SD_00000000"}),
    )

    assert resp.status_code == 403
    assert resp.json["message"] == "Unauthorized"
    assert auth0_key_mock.call_count == 1


@mock_s3
def test_service_token(auth0_key_mock, service_token):
    app.config["TOKEN"] = "abc123"
    app.config["AUTH0_JWKS"] = "https://auth0/jwks.json"
    app_context = app.app_context()
    app_context.push()
    client = app.test_client()

    resp = client.post(
        "/buckets",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {service_token()}",
        },
        data=json.dumps({"study_id": "SD_00000000"}),
    )

    assert resp.status_code == 201


@mock_s3
def test_other_token(auth0_key_mock, service_token):
    """
    Test that non-service tokens will fail
    """
    app.config["TOKEN"] = "abc123"
    app.config["AUTH0_JWKS"] = "https://auth0/jwks.json"
    app_context = app.app_context()
    app_context.push()
    client = app.test_client()

    resp = client.post(
        "/buckets",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {service_token(gty='user')}",
        },
        data=json.dumps({"study_id": "SD_00000000"}),
    )

    assert resp.status_code == 403
