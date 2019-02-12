import boto3
import json
import pytest
from flask import url_for
from service import app
from moto import mock_s3


def test_status(client):
    resp = client.get('/status')
    assert resp.status_code == 200
    assert 'name' in json.loads(resp.data.decode())
    assert 'version' in json.loads(resp.data.decode())


@mock_s3
def test_my_model_save(client, logging_bucket):
    logging_bucket()
    s3 = boto3.client('s3')

    resp = client.post('/buckets',
                       headers={'Content-Type': 'application/json'},
                       data=json.dumps({'study_id': 'SD_00000000'}))

    assert resp.status_code == 201

    resp = json.loads(resp.data.decode())
    assert 'message' in resp
    assert resp['message'].startswith('created')
    assert resp['message'].endswith('sd-00000000')

    bucket = resp['message'].replace('created ', '')
    assert len(s3.list_buckets()['Buckets']) == 4
    assert s3.list_buckets()['Buckets'][2]['Name'] == bucket
    assert s3.list_buckets()['Buckets'][3]['Name'] == 'kf-study-us-west-2-dev-sd-00000000-dr'

    # Introspect bucket for correct settings
    bucket = boto3.resource('s3').Bucket(bucket)

    assert bucket.Versioning().status == 'Enabled'
    assert bucket.Logging().logging_enabled == {
        'TargetBucket': 'kf-s3-data-logging-bucket',
        'TargetPrefix': 'studies/dev/sd-00000000/'
    }


@mock_s3
def test_bucket_list(client, logging_bucket):
    logging_bucket()
    s3 = boto3.client('s3')

    for i in range(10):
        resp = client.post('/buckets',
                           headers={'Content-Type': 'application/json'},
                           data=json.dumps({'study_id': 'SD_0000000'+str(i)}))
        assert resp.status_code == 201

    assert len(s3.list_buckets()['Buckets']) == 22

    resp = client.get('/buckets')
    assert resp.status_code == 200
    resp = json.loads(resp.data.decode())
    assert 'buckets' in resp
    assert len(resp['buckets']) == 22


@mock_s3
def test_bad_study(client, logging_bucket):
    logging_bucket()
    s3 = boto3.client('s3')

    resp = client.post('/buckets',
                       headers={'Content-Type': 'application/json'},
                       data=json.dumps({'study_id': 'INVALID'}))

    assert resp.status_code == 400
    resp = json.loads(resp.data.decode())
    assert 'message' in resp
    assert 'not a valid study_id' in resp['message']
    assert len(s3.list_buckets()['Buckets']) == 2


@mock_s3
def test_no_study(client, logging_bucket):
    s3 = boto3.client('s3')
    logging_bucket()

    resp = client.post('/buckets',
                       headers={'Content-Type': 'application/json'},
                       data=json.dumps({}))

    assert resp.status_code == 400
    resp = json.loads(resp.data.decode())
    assert 'message' in resp
    assert 'expected study_id in body' in resp['message']
    assert len(s3.list_buckets()['Buckets']) == 2
