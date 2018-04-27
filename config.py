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
