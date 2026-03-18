import sys
import os
import base64
import json
import yaml
import click

from cryptography.fernet import Fernet

import confidant.clients
from confidant import settings
from confidant.lib import cryptolib


@click.command()
@click.option('--in', '_in', default='-', help='Path to YAML file containing all the secrets')
@click.option('--out', '_out', default='-')
def generate_secrets_bootstrap(_in, _out):
    """
    Generate encrypted blob from a file
    """
    if _in == '-':
        secrets = sys.stdin.read()
    else:
        with open(os.path.join(_in), 'r') as f:
            secrets = f.read()
    client = confidant.clients.get_boto_client(
        'kms',
        endpoint_url=settings.KMS_URL,
    )
    data_key = cryptolib.create_datakey(
        {'type': 'bootstrap'},
        settings.KMS_MASTER_KEY,
        client=client,
    )
    f = Fernet(data_key['plaintext'])
    data = {
        'data_key': base64.b64encode(
            data_key['ciphertext'],
        ).decode('utf-8'),
        'secrets': f.encrypt(secrets.encode('utf-8')).decode('utf-8'),
    }
    data = json.dumps(data)
    if _out == '-':
        print(data)
    else:
        with open(os.path.join(_out), 'w') as f:
            f.write(data)


@click.command()
@click.option('--out', '_out', default='-')
def decrypt_secrets_bootstrap(_out):
    """
    Show the YAML formatted secrets_bootstrap in a decrypted form
    """
    data = settings.encrypted_settings.get_all_secrets()
    data = yaml.safe_dump(data, default_flow_style=False, indent=2)
    if _out == '-':
        print(data)
    else:
        with open(os.path.join(_out), 'w') as f:
            f.write(data)
