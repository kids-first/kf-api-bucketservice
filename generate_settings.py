import os
import json


def gen_env(env):
    settings = {
        "app_function": "service.app",
        "aws_region": "us-east-1",
        "profile_name": "default",
        "project_name": "kf-api-bucketservice",
        "runtime": "python3.6",
        "manage_roles": False,
        "profile_name": None,
        "role_name": "kf-bucket-creator-lambda-dev-role",
        "role_arn": "arn:aws:iam::538745987955:role/kf-bucket-creator-lambda-dev-role",
        "s3_bucket": "kf-api-us-east-1-dev-bucketservice",
        "keep_warm": False,
        "manage_roles": False,
        "vpc_config": {
            "SubnetIds": [ "subnet-7355cd4c", "subnet-b70e8bea" ],
            "SecurityGroupIds": [ "sg-733c9b3a" ]
        },
        "iam_authorization": False
    }

    if 'TOKEN' in os.environ:
        settings["aws_environment_variables"] = {
            "TOKEN": os.environ.get('TOKEN', '')
        }

    return settings


config = {}
for env in ['dev', 'qa', 'prd']:
    config[env] = gen_env(env)

with open('generated_settings.json', 'w') as f:
    json.dump(config, f)
