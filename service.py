import os
import jwt
import json
import boto3
import requests
from functools import wraps
from flask import Flask, current_app, request, jsonify, abort
from werkzeug.exceptions import HTTPException


POLICY = """{{
      "Version": "2012-10-17",
      "Id": "kf001",
      "Statement": [
          {{
              "Sid": "DenyDeleteObject",
              "Effect": "Deny",
              "Principal": "*",
              "Action": [
                "s3:DeleteObjectTagging",
                "s3:DeleteObjectVersionTagging",
                "s3:DeleteObjectVersion",
                "s3:DeleteObject"
              ],
              "Resource": "arn:aws:s3:::{bucket_name}/*"
          }},
          {{
              "Sid": "DenyDeleteBucket",
              "Effect": "Deny",
              "Principal": "*",
              "Action": [
                "s3:DeleteBucket"
              ],
              "Resource": "arn:aws:s3:::{bucket_name}"
          }}
      ]
}}"""


def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    @app.errorhandler(400)
    def json_error(error):
        description = "error"
        code = 500
        if hasattr(error, "description"):
            description = error.description
        if hasattr(error, "code"):
            code = error.code
        return jsonify({"message": description}), code

    from werkzeug.exceptions import default_exceptions

    for ex in default_exceptions:
        app.register_error_handler(ex, json_error)

    return app


app = create_app()


def get_bucket_name(study_id):
    return "kf-study-{}-{}-{}".format(
        current_app.config["REGION"],
        current_app.config["STAGE"],
        study_id.replace("_", "-"),
    ).lower()


def get_auth0_key():
    """
    Get a public key from Auth0's JWKS
    Reformat the JWKS into a PEM format
    """
    resp = requests.get(current_app.config["AUTH0_JWKS"], timeout=10)
    key = resp.json()["keys"][0]
    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
    return public_key


def authenticate(f):
    """
    Authenticate a request's token with vault or tries to verify a JWT against
    Auth0
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        logger = current_app.logger

        # Using a shared secret token
        secret_token = current_app.config["TOKEN"]
        if 'Bearer' not in request.headers.get("Authorization", ""):
            return abort(403, "Unauthorized")
        token = request.headers.get("Authorization", "").split("Bearer ")[-1]

        if token == secret_token:
            return f(*args, **kwargs)

        # Try to verify via Auth0
        try:
            public_key = get_auth0_key()
            token = jwt.decode(
                token,
                public_key,
                algorithms="RS256",
                options={"verify_aud": False},
            )
        except (TypeError, KeyError):
            # If we had trouble getting JWKS
            return abort(403, "Unauthorized")
        except jwt.exceptions.DecodeError as err:
            logger.error(f"Problem authenticating request: {err}")
            return abort(403, "Unauthorized")
        except jwt.exceptions.InvalidTokenError as err:
            logger.error(f"Token provided is not valid: {err}")
            return abort(403, "Unauthorized")

        # Make sure that a service is invoking the bucket creation
        if not token.get("gty") == "client-credentials":
            return abort(403, "Unauthorized")

        return f(*args, **kwargs)

    return wrapper


def parse_request(req):
    """ Parse fields from post body """
    # Parsing out the request body
    data = req.get_json()
    if data is None or "study_id" not in data:
        abort(400, "expected study_id in body")

    study_id = data["study_id"]

    if len(study_id) != 11 or study_id[:3] != "SD_":
        abort(400, "not a valid study_id")

    return study_id


@app.route("/status", methods=["GET"])
def status():
    return jsonify({"name": "Bucket Creation Service", "version": "1.3.0"})


@app.route("/buckets", methods=["POST"])
@authenticate
def new_bucket():
    """
    Create a new bucket in s3 given a study_id
    """
    logger = current_app.logger

    study_id = parse_request(request)
    s3 = boto3.client("s3")
    bucket_name = get_bucket_name(study_id)
    bucket = s3.create_bucket(ACL="private", Bucket=bucket_name)
    _add_policy(bucket_name)

    # Encryption
    _add_encryption(bucket_name)

    # Tagging
    _add_tagging(bucket_name, study_id)

    # Versioning
    _add_versioning(bucket_name)

    # Logging
    _add_logging(bucket_name)

    # CORS
    _add_cors(bucket_name)

    # Replication
    _add_replication(bucket_name)

    # Inventory
    _add_inventory(bucket_name)

    return (
        jsonify(
            {
                "message": "created {}".format(bucket_name),
                "bucket": bucket_name,
            }
        ),
        201,
    )


def _add_versioning(bucket_name):
    """
    Enabled versioning for a bucket
    """
    s3 = boto3.client("s3")
    response = s3.put_bucket_versioning(
        Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"}
    )
    return response


def _add_encryption(bucket_name):
    """
    Adds encryption to a bucket
    """
    s3 = boto3.client("s3")
    response = s3.put_bucket_encryption(
        Bucket=bucket_name,
        ServerSideEncryptionConfiguration={
            "Rules": [
                {
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256"
                    }
                }
            ]
        },
    )
    return response


def _add_tagging(bucket_name, study_id):
    """
    Adds standard tag set to a bucket
    """
    s3 = boto3.client("s3")
    response = s3.put_bucket_tagging(
        Bucket=bucket_name,
        Tagging={
            "TagSet": [
                {"Key": "Name", "Value": f"{study_id}"},
                {
                    "Key": "Description",
                    "Value": f"harmonized and source files for {study_id}",
                },
                {"Key": "Environment", "Value": current_app.config["STAGE"]},
                {"Key": "AppId", "Value": "kf-api-bucket-service"},
                {"Key": "Owner", "Value": "d3b"},
                {"Key": "kf_id", "Value": study_id},
            ]
        },
    )
    return response


def _add_logging(bucket_name):
    """
    Adds access logging to a bucket
    """
    logger = current_app.logger
    s3 = boto3.client("s3")
    # Logging buckets need to be in the same region, determine based on name
    if "-dr" in bucket_name:
        target_logging_bucket = current_app.config["DR_LOGGING_BUCKET"]
    else:
        target_logging_bucket = current_app.config["LOGGING_BUCKET"]
    # Go to logging bucket under STAGE/STUDY_ID{-dr}/
    s = bucket_name.find("sd-")
    study_id = bucket_name[s : s + 11]
    if bucket_name.endswith("-dr"):
        study_id += "-dr"
    log_prefix = f"studies/{current_app.config['STAGE']}/{study_id}/"
    try:
        response = s3.put_bucket_logging(
            Bucket=bucket_name,
            BucketLoggingStatus={
                "LoggingEnabled": {
                    "TargetBucket": target_logging_bucket,
                    "TargetPrefix": log_prefix,
                }
            },
        )
        return response
    except s3.exceptions.ClientError as err:
        if err.response["Error"]["Code"] == "InvalidTargetBucketForLogging":
            logger.error(
                f"logging not enabled, log bucket not found "
                + f"{target_logging_bucket}"
            )
        else:
            logger.error(err)


def _add_replication(bucket_name):
    """
    Configures a second bucket with `-dr` suffix and replicates the primary
    bucket to it.
    Adds a lifecycle policy to the dr bucket to immediately roll data into
    glacier for cold storage
    """
    logger = current_app.logger
    dr_bucket_name = f"{bucket_name}-dr"
    dr_bucket_name = dr_bucket_name.replace("us-east-1", "us-west-2")
    study_id = ""
    if bucket_name[-11:].startswith("sd-"):
        study_id = bucket_name[-11:]

    s3 = boto3.client("s3")
    # Set up a second -dr bucket to replicate to
    try:
        bucket = s3.create_bucket(
            ACL="private",
            Bucket=dr_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
        )
        _add_policy(dr_bucket_name)
    except s3.exceptions.ClientError as err:
        if err.response["Error"]["Code"] == "BucketAlreadyOwnedByYou":
            logger.info(f"bucket {dr_bucket_name} already exists, continueing")

    logger.info("adding encryption to replicated bucket")
    _add_encryption(dr_bucket_name)
    logger.info("adding versioning to replicated bucket")
    _add_versioning(dr_bucket_name)
    logger.info("adding tagging to replicated bucket")
    _add_tagging(dr_bucket_name, study_id)
    logger.info("adding logging to replicated bucket")
    _add_logging(dr_bucket_name)

    # Add the replication rule
    iam_role = f"arn:aws:iam::538745987955:role/kf-s3-study-replication-{current_app.config['STAGE']}-role"
    response = s3.put_bucket_replication(
        Bucket=bucket_name,
        ReplicationConfiguration={
            "Role": iam_role,
            "Rules": [
                {
                    "ID": "string",
                    "Status": "Enabled",
                    "Prefix": "",
                    "Destination": {
                        "Bucket": "arn:aws:s3:::" + dr_bucket_name,
                        "StorageClass": "GLACIER",
                    },
                }
            ],
        },
    )

    return response


def _add_cors(bucket):
    """
    Adds CORS for Cavatica requests
    """
    client = boto3.client("s3")
    return client.put_bucket_cors(
        Bucket=bucket,
        CORSConfiguration={
            "CORSRules": [
                {
                    "AllowedHeaders": [
                        "Authorization",
                        "Content-Range",
                        "Accept",
                        "Content-Type",
                        "Origin",
                        "Range",
                    ],
                    "AllowedMethods": ["GET"],
                    "AllowedOrigins": ["https://cavatica.sbgenomics.com"],
                    "ExposeHeaders": [
                        "Content-Range",
                        "Content-Length",
                        "ETag",
                    ],
                    "MaxAgeSeconds": 3000,
                }
            ]
        },
    )


def _add_policy(bucket):
    """
    Adds a policy to the bucket. Will replace whatever policy already exists,
    if there is one.
    """
    client = boto3.client("s3")
    policy = POLICY.format(bucket_name=bucket)
    return client.put_bucket_policy(Bucket=bucket, Policy=policy)


def _add_inventory(bucket):
    """
    Adds inventory configuration to a bucket
    """
    client = boto3.client("s3")
    dest = "arn:aws:s3:::{}".format(current_app.config["INVENTORY_DEST"])

    return client.put_bucket_inventory_configuration(
        Bucket=bucket,
        Id="StudyBucketInventory",
        InventoryConfiguration={
            "Destination": {
                "S3BucketDestination": {
                    "Bucket": dest,
                    "Format": "CSV",
                    "Prefix": "inventories",
                    "Encryption": {"SSES3": {}},
                }
            },
            "IsEnabled": True,
            "Id": "StudyBucketInventory",
            "IncludedObjectVersions": "All",
            "OptionalFields": [
                "Size",
                "LastModifiedDate",
                "StorageClass",
                "ETag",
                "IsMultipartUploaded",
                "ReplicationStatus",
                "EncryptionStatus",
                "ObjectLockRetainUntilDate",
                "ObjectLockMode",
                "ObjectLockLegalHoldStatus",
            ],
            "Schedule": {"Frequency": "Weekly"},
        },
    )


@app.route("/buckets", methods=["GET"])
@authenticate
def list_buckets():
    """
    List study buckets
    """
    s3 = boto3.client("s3")
    buckets = s3.list_buckets()
    return jsonify({"buckets": buckets["Buckets"]}), 200


if __name__ == "__main__":
    """
    When run from cli, retrospectively set up any existing buckets to make
    sure everything is configured consistently. Sort of like a migration.
    """
    s3 = boto3.client("s3")
    buckets = s3.list_buckets()

    buckets = [
        b["Name"]
        for b in buckets["Buckets"]
        if b["Name"].startswith("kf-study-us-east-1-prd-sd-")
    ]
    s3 = boto3.client("s3")

    print(
        f"!!! WARNING !!! About to run in the {os.environ['STAGE']} enviornment"
    )
    command = input(
        f"found {len(buckets)} study buckets to apply changes to"
        ", type Y to proceed: "
    )
    if not command.lower() == "y":
        print("aborting")
        exit()

    with app.app_context():
        for bucket_name in buckets:
            print(f"===> PATCHING BUCKET {bucket_name}")
            if bucket_name.endswith("-dr"):
                continue
            study_id = bucket_name[-11:]
            print("setting up:", study_id)

            # Encryption
            print("enabling encryption")
            resp = _add_encryption(bucket_name)
            assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

            # Tagging
            print("adding tagging")
            resp = _add_tagging(bucket_name, study_id)
            assert resp["ResponseMetadata"]["HTTPStatusCode"] == 204

            # Versioning
            print("add versioning")
            resp = _add_versioning(bucket_name)
            assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

            # Logging
            print("add logging")
            resp = _add_logging(bucket_name)
            assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

            # Replication
            print("add replication")
            resp = _add_replication(bucket_name)
            assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

            # CORS
            print("add CORS")
            resp = _add_cors(bucket_name)
            assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

            # Add policy
            print("add policy")
            resp = _add_policy(bucket_name)
            assert resp["ResponseMetadata"]["HTTPStatusCode"] == 204

            # Add inventory
            print("add inventory")
            resp = _add_inventory(bucket_name)
            assert resp["ResponseMetadata"]["HTTPStatusCode"] == 204
