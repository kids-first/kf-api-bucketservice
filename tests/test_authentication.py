import boto3
import json
import jwt
import pytest
import datetime
from flask import url_for
from service import app
from unittest.mock import patch
from moto import mock_s3


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
