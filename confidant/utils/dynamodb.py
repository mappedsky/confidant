import base64
import json

from confidant import settings
from confidant.services.dynamodbstore import store


def create_dynamodb_tables():
    store.initialize()


def encode_last_evaluated_key(last_evaluated_key):
    if not last_evaluated_key:
        return None
    str_key = json.dumps(last_evaluated_key)
    return base64.b64encode(str_key.encode('UTF-8')).decode('UTF-8')


def decode_last_evaluated_key(last_evaluated_key):
    if not last_evaluated_key:
        return None
    return json.loads(base64.b64decode(last_evaluated_key))
