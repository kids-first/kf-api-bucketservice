import boto3
import pytest
from service import _add_replication
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
