import boto3
import json
import pytest
from flask import url_for
from service import create_app, app
from moto import mock_s3


@pytest.yield_fixture(scope='session')
def client():
    app_context = app.app_context()
    app_context.push()
    yield app.test_client()


def test_status(client):
    resp = client.get('/status')
    assert resp.status_code == 200
    assert 'name' in json.loads(resp.data)
    assert 'version' in json.loads(resp.data)


@mock_s3
def test_my_model_save(client):
    s3 = boto3.client('s3')

    resp = client.post('/buckets',
                       headers={'Content-Type': 'application/json'},
                       data=json.dumps({'study_id': 'SD_00000000'}))

    assert resp.status_code == 201

    resp = json.loads(resp.data)
    assert 'message' in resp
    assert resp['message'].startswith('created')
    assert resp['message'].endswith('sd-00000000')

    bucket = resp['message'].replace('created ', '')
    assert len(s3.list_buckets()['Buckets']) == 1
    assert s3.list_buckets()['Buckets'][0]['Name'] == bucket


@mock_s3
def test_bucket_list(client):
    s3 = boto3.client('s3')

    for i in range(10):
        resp = client.post('/buckets',
                           headers={'Content-Type': 'application/json'},
                           data=json.dumps({'study_id': 'SD_0000000'+str(i)}))
        assert resp.status_code == 201

    assert len(s3.list_buckets()['Buckets']) == 10

    resp = client.get('/buckets')
    assert resp.status_code == 200
    resp = json.loads(resp.data)
    assert 'buckets' in resp
    assert len(resp['buckets']) == 10


@mock_s3
def test_bad_study(client):
    s3 = boto3.client('s3')

    resp = client.post('/buckets',
                       headers={'Content-Type': 'application/json'},
                       data=json.dumps({'study_id': 'INVALID'}))

    assert resp.status_code == 400
    resp = json.loads(resp.data)
    assert 'message' in resp
    assert 'not a valid study_id' in resp['message']
    assert len(s3.list_buckets()['Buckets']) == 0


@mock_s3
def test_no_study(client):
    s3 = boto3.client('s3')

    resp = client.post('/buckets',
                       headers={'Content-Type': 'application/json'},
                       data=json.dumps({}))

    assert resp.status_code == 400
    resp = json.loads(resp.data)
    assert 'message' in resp
    assert 'expected study_id in body' in resp['message']
    assert len(s3.list_buckets()['Buckets']) == 0
