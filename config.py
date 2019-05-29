import os


class Config():
    # Load vars from settings file into environment if in local
    if ('SERVERTYPE' not in os.environ):
        import json
        import os
        json_data = open('zappa_settings.json')
        env_vars = json.load(json_data)['dev']['aws_environment_variables']
        for key, val in env_vars.items():
            os.environ[key] = val

    STAGE = os.environ.get('STAGE', 'dev')
    REGION = os.environ.get('REGION', 'us-east-1')
    TOKEN = os.environ.get('TOKEN', '')
    LOGGING_BUCKET = os.environ.get('LOGGING_BUCKET',
                                    'kf-s3-data-logging-bucket')

    INVENTORY_DEST = os.environ.get("INVENTORY_DEST", LOGGING_BUCKET)

    DR_LOGGING_BUCKET = os.environ.get('DR_LOGGING_BUCKET',
                                       'kf-dr-s3-data-logging-bucket')


    # Try to load from vault
    if 'BUCKET_SERVER_SECRET' in os.environ:
        import hvac
        import boto3
        session = boto3.Session()
        credentials = session.get_credentials()

        vault_url = os.environ.get('VAULT_URL', 'https://vault:8200/')
        vault_role = os.environ.get('VAULT_ROLE', 'DataserviceRole')
        bucket_token = os.environ.get('BUCKET_SERVER_SECRET', None)

        client = hvac.Client(url=vault_url)
        client.auth_aws_iam(credentials.access_key,
                            credentials.secret_key,
                            credentials.token)
        bucket_token = client.read(bucket_token) if bucket_token else None
        if (bucket_token and
            'data' in bucket_token and
            'token' in bucket_token['data']):
            TOKEN = bucket_token['data']['token']

        client.logout()
