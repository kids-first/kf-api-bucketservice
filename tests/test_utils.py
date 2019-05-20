import json
import boto3
import pytest
from service import _add_replication, _add_cors, _add_policy
from moto import mock_s3


@mock_s3
def test_replication(client, logging_bucket):
    """
    Test that adding replication to a bucket configures a dr bucket correctly
    """
    logging_bucket()
    bucket_name = 'sd-00000000'

    client = boto3.client('s3')
    bucket = client.create_bucket(ACL='private', Bucket=bucket_name)

    _add_replication(bucket_name)

    dr_bucket_name = f'{bucket_name}-dr'
    bucket = boto3.resource('s3').Bucket(dr_bucket_name)

    assert len(bucket.Tagging().tag_set) == 6
    assert bucket.Versioning().status == 'Enabled'

    logging = bucket.Logging().logging_enabled
    assert logging['TargetBucket'] == 'kf-dr-s3-data-logging-bucket'
    assert logging['TargetPrefix'] == 'studies/dev/sd-00000000-dr/'


@mock_s3
def test_cors(client, logging_bucket):
    """
    Test that buckets created have CORS for cavatica
    """
    logging_bucket()
    bucket_name = "sd-00000000"

    client = boto3.client("s3")
    s3 = boto3.resource("s3")
    client.create_bucket(ACL="private", Bucket=bucket_name)
    _add_cors(bucket_name)

    rules = s3.BucketCors(bucket_name).cors_rules
    assert len(rules) == 1
    assert rules[0]["AllowedOrigins"] == ["https://cavatica.sbgenomics.com"]


@mock_s3
def test_no_delete_policy(client, logging_bucket):
    """
    Test that buckets created have Delete* actions denied
    """
    logging_bucket()
    bucket_name = 'sd-00000000'

    def policy_check(policy, bucket):
        assert policy['Statement'][0]['Sid'] == 'DenyDeleteObject'
        assert policy['Statement'][0]['Resource'] == f"arn:aws:s3:::{bucket}/*"
        assert policy['Statement'][1]['Sid'] == 'DenyDeleteBucket'
        assert policy['Statement'][1]['Resource'] == f"arn:aws:s3:::{bucket}"

    client = boto3.client('s3')
    s3 = boto3.resource('s3')
    client.create_bucket(ACL='private', Bucket=bucket_name)
    _add_policy(bucket_name)
    policy = json.loads(s3.BucketPolicy(bucket_name).policy)
    policy_check(policy, bucket_name)

    # Adding replication will make a replicated bucket that should also have
    # the policy on it
    resp = _add_replication(bucket_name)
    dr_bucket_name = f'{bucket_name}-dr'

    policy = json.loads(s3.BucketPolicy(dr_bucket_name).policy)
    policy_check(policy, dr_bucket_name)
