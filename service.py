import os
import json
import boto3
from functools import wraps
from flask import Flask, current_app, request, jsonify, abort
from werkzeug.exceptions import HTTPException


def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    @app.errorhandler(400)
    def json_error(error):
        description = 'error'
        code = 500
        if hasattr(error, 'description'):
            description = error.description
        if hasattr(error, 'code'):
            code = error.code
        return jsonify({'message': description}), code

    from werkzeug.exceptions import default_exceptions
    for ex in default_exceptions:
        app.register_error_handler(ex, json_error)

    return app


app = create_app()


def get_bucket_name(study_id):
    return 'kf-study-{}-{}-{}'.format(current_app.config['REGION'],
                                      current_app.config['STAGE'],
                                      study_id.replace('_', '-')).lower()


def authenticate(f):
    """ Authenticate a request's token with vault """
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = current_app.config['TOKEN']
        allow = request.headers.get('Authorization', '').replace('Bearer ', '') == token
        if not allow:
            return abort(403, 'Unauthorized')
        return f(*args, **kwargs)
    return wrapper


def parse_request(req):
    """ Parse fields from post body """
    # Parsing out the request body
    data = req.get_json()
    if (data is None or
        'study_id' not in data):
        abort(400, 'expected study_id in body')

    study_id = data['study_id']

    if len(study_id) != 11 or study_id[:3] != 'SD_':
        abort(400, 'not a valid study_id')

    return study_id


@app.route("/status", methods=['GET'])
def status():
    return jsonify({'name': 'Bucket Creation Service',
                    'version': '1.1.0'})


@app.route("/buckets", methods=['POST'])
@authenticate
def new_bucket():
    """
    Create a new bucket in s3 given a study_id
    """
    study_id = parse_request(request)
    s3 = boto3.client("s3")
    bucket_name = get_bucket_name(study_id)
    bucket = s3.create_bucket(
            ACL='private',
            Bucket=bucket_name)

    s3.put_bucket_encryption(
        Bucket=bucket_name,
        ServerSideEncryptionConfiguration={
            'Rules': [
                {
                    'ApplyServerSideEncryptionByDefault': {
                        'SSEAlgorithm': 'AES256',
                    }
                },
            ]
        }
    )

    # Tagging
    s3.put_bucket_tagging(
        Bucket=bucket_name,
        Tagging={
            'TagSet': [
                {
                    'Key': 'Name',
                    'Value': f'{study_id}'
                },
                {
                    'Key': 'Description',
                    'Value': f'harmonized and source files for {study_id}'
                },
                {
                    'Key': 'Environment',
                    'Value': current_app.config['STAGE']
                },
                {
                    'Key': 'AppId',
                    'Value': 'kf-api-bucket-service'
                },
                {
                    'Key': 'Owner',
                    'Value': 'd3b'
                },
                {
                    'Key': 'kf_id',
                    'Value': study_id
                },
            ]
        }
    )
    
    # Versioning
    response = s3.put_bucket_versioning(
        Bucket=bucket_name,
        VersioningConfiguration={
            'Status': 'Enabled'
        }
    )

    return jsonify({'message': 'created {}'.format(bucket_name)}), 201
    

@app.route("/buckets", methods=['GET'])
@authenticate
def list_buckets():
    """
    List study buckets
    """
    s3 = boto3.client("s3")
    buckets = s3.list_buckets()
    return jsonify({'buckets': buckets['Buckets']}), 200
