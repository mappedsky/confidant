import base64
import copy
import json
import logging
import re
import uuid
from datetime import datetime
from datetime import timedelta
from datetime import timezone

from confidant import settings
from confidant.schema.secrets import RevisionsResponse
from confidant.schema.secrets import SecretResponse
from confidant.schema.secrets import SecretsResponse
from confidant.services import keymanager
from confidant.services.ciphermanager import CipherManager
from confidant.services.dynamodbstore import store
from confidant.utils import stats

logger = logging.getLogger(__name__)


def _strip_empty_values(value):
    if isinstance(value, dict):
        return {
            key: stripped
            for key, child in value.items()
            if (stripped := _strip_empty_values(child)) is not None
        } or None
    if isinstance(value, list):
        stripped = [
            child
            for child in (_strip_empty_values(v) for v in value)
            if child is not None
        ]
        return stripped or None
    if isinstance(value, tuple):
        stripped = tuple(
            child
            for child in (_strip_empty_values(v) for v in value)
            if child is not None
        )
        return stripped or None
    if isinstance(value, set):
        stripped = {
            child
            for child in (_strip_empty_values(v) for v in value)
            if child is not None
        }
        return stripped or None
    if value in (None, ""):
        return None
    return value


def _as_datetime(value):
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def _next_rotation_date(item):
    tags = item.get("tags", [])
    if len(set(tags) & set(settings.TAGS_EXCLUDING_ROTATION)) > 0:
        return None

    last_rotation_date = _as_datetime(item.get("last_rotation_date"))
    last_decrypted_date = _as_datetime(item.get("last_decrypted_date"))

    if last_rotation_date is None:
        return datetime.now(timezone.utc)
    if last_decrypted_date and last_decrypted_date > last_rotation_date:
        return last_decrypted_date

    days = settings.MAXIMUM_ROTATION_DAYS
    for tag in tags:
        rotation_days = settings.ROTATION_DAYS_CONFIG.get(tag)
        if rotation_days is None:
            continue
        if days is None or rotation_days < days:
            days = rotation_days
    return last_rotation_date + timedelta(days=days)


def _secret_response_from_item(
    item,
    include_secret_keys=False,
    include_secret_pairs=False,
):
    data = {
        "tenant_id": item["tenant_id"],
        "id": item["id"],
        "name": item["name"],
        "revision": int(item["revision"]),
        "modified_date": _as_datetime(item["modified_date"]),
        "modified_by": item["modified_by"],
    }
    if item.get("metadata") is not None:
        data["metadata"] = item["metadata"]
    if item.get("documentation") is not None:
        data["documentation"] = item["documentation"]
    if item.get("tags") is not None:
        data["tags"] = item["tags"]
    if item.get("last_rotation_date") is not None:
        data["last_rotation_date"] = _as_datetime(item["last_rotation_date"])
    data["next_rotation_date"] = _next_rotation_date(item)

    if include_secret_keys:
        data["secret_keys"] = item.get("secret_keys", [])
    if include_secret_pairs:
        data["secret_pairs"] = _decrypt_secret_pairs(item)
    return SecretResponse(**data)


def _save_last_decryption_time(tenant_id, secret_id, item=None):
    if not settings.ENABLE_SAVE_LAST_DECRYPTION_TIME:
        return item
    last_decrypted_date = datetime.now(timezone.utc).isoformat()
    store.update_secret_last_decrypted_date(
        tenant_id,
        secret_id,
        last_decrypted_date,
    )
    if item is not None:
        item = copy.deepcopy(item)
        item["last_decrypted_date"] = last_decrypted_date
    return item


def _decrypt_secret_pairs(item):
    if not item.get("secret_pairs"):
        return {}
    data_key = item["data_key"]
    if isinstance(data_key, str):
        data_key = base64.b64decode(data_key.encode("UTF-8"))
    context = {
        "id": item["id"],
        "tenant_id": item["tenant_id"],
    }
    data_key = keymanager.decrypt_datakey(
        data_key,
        encryption_context=context,
    )
    cipher = CipherManager(data_key, item.get("cipher_version"))
    decrypted = cipher.decrypt(item["secret_pairs"])
    return json.loads(decrypted)


def _encrypt_secret_pairs(tenant_id, secret_id, secret_pairs):
    data_key = keymanager.create_datakey(
        encryption_context={"id": secret_id, "tenant_id": tenant_id}
    )
    cipher = CipherManager(data_key["plaintext"], version=2)
    encrypted_pairs = cipher.encrypt(json.dumps(secret_pairs))
    if isinstance(data_key["ciphertext"], bytes):
        data_key = base64.b64encode(data_key["ciphertext"]).decode("UTF-8")
    else:
        data_key = data_key["ciphertext"]
    return encrypted_pairs, data_key, 2


def get_secrets(
    tenant_id,
    secret_ids,
    include_secret_keys=False,
    include_secret_pairs=False,
):
    with stats.timer("service_batch_get_secrets"):
        _secret_ids = copy.deepcopy(secret_ids)
        secrets = []
        for secret_id in _secret_ids:
            item = store.get_secret_latest(tenant_id, secret_id)
            if item:
                secrets.append(
                    _secret_response_from_item(
                        item,
                        include_secret_keys=include_secret_keys,
                        include_secret_pairs=include_secret_pairs,
                    )
                )
        return secrets


def list_secrets(tenant_id, limit=None, page=None):
    results = store.list_secrets(
        tenant_id,
        limit=limit,
        last_evaluated_key=page,
    )
    items = results.get("Items", [])
    secrets = [_secret_response_from_item(item) for item in items]
    return SecretsResponse.from_secrets(
        secrets,
        next_page=results.get("LastEvaluatedKey"),
    )


def get_secret_latest(
    tenant_id,
    secret_id,
    metadata_only=False,
    alert_on_access=False,
):
    item = (
        store.get_secret_metadata(tenant_id, secret_id)
        if metadata_only
        else store.get_secret_latest(tenant_id, secret_id)
    )
    if not item:
        return None
    if not metadata_only and alert_on_access:
        item = _save_last_decryption_time(tenant_id, secret_id, item)
    return _secret_response_from_item(
        item,
        include_secret_keys=True,
        include_secret_pairs=not metadata_only,
    )


def list_secret_versions(tenant_id, secret_id):
    items = store.list_secret_versions(tenant_id, secret_id)
    secrets = [
        _secret_response_from_item(
            item,
            include_secret_keys=True,
            include_secret_pairs=False,
        )
        for item in items
    ]
    return RevisionsResponse.from_secrets(secrets)


def get_secret_version(tenant_id, secret_id, version, alert_on_access=False):
    item = store.get_secret_version(tenant_id, secret_id, version)
    if not item:
        return None
    if alert_on_access:
        item = _save_last_decryption_time(tenant_id, secret_id, item)
    return _secret_response_from_item(
        item,
        include_secret_keys=True,
        include_secret_pairs=True,
    )


def check_secret_pair_values(secret_pairs):
    for key, val in secret_pairs.items():
        if isinstance(val, dict) or isinstance(val, list):
            ret = {"error": "secret pairs must be key: value"}
            return (False, ret)
        if re.search(r"\s", key):
            ret = {"error": "secret key must not contain whitespace"}
            return (False, ret)
    return (True, {})


def lowercase_secret_pairs(secret_pairs):
    return {i.lower(): j for i, j in secret_pairs.items()}


def get_revision_ids_for_secret(secret):
    _range = range(1, secret.revision + 1)
    ids = []
    for i in _range:
        ids.append(f"{secret.id}-{i}")
    return ids


def get_latest_secret_revision(_id, revision):
    return revision + 1


def _build_secret_items(
    tenant_id,
    secret_id,
    name,
    revision,
    secret_keys,
    secret_pairs,
    data_key,
    cipher_version,
    metadata,
    modified_by,
    documentation,
    tags,
    last_rotation_date,
    last_decrypted_date,
    created_at,
    previous_created_at=None,
):
    base = {
        "tenant_id": tenant_id,
        "id": secret_id,
        "name": name,
        "revision": revision,
        "metadata": metadata,
        "modified_date": created_at,
        "modified_by": modified_by,
        "documentation": documentation,
        "tags": tags,
        "last_decrypted_date": last_decrypted_date,
        "last_rotation_date": last_rotation_date,
        "secret_keys": list(secret_keys),
        "secret_pairs": secret_pairs,
        "data_key": data_key,
        "cipher_version": cipher_version,
    }
    metadata_item = {
        "PK": f"TENANT#{tenant_id}#SECRET#{secret_id}",
        "SK": "#METADATA",
        **base,
    }
    latest_item = {
        "PK": f"TENANT#{tenant_id}#SECRET#{secret_id}",
        "SK": "#LATEST",
        **base,
    }
    version_item = {
        "PK": f"TENANT#{tenant_id}#SECRET#{secret_id}",
        "SK": f"VERSION#{revision:010d}",
        **base,
    }
    list_item = {
        "PK": f"TENANT#{tenant_id}#SECRET_LIST",
        "SK": f"SECRET#{secret_id}",
        "tenant_id": tenant_id,
        "id": secret_id,
        "name": name,
        "revision": revision,
        "metadata": metadata,
        "modified_date": created_at,
        "modified_by": modified_by,
        "documentation": documentation,
        "tags": tags,
        "last_decrypted_date": last_decrypted_date,
        "last_rotation_date": last_rotation_date,
        "secret_keys": list(secret_keys),
    }
    if previous_created_at is not None:
        metadata_item["created_at"] = previous_created_at
        latest_item["created_at"] = previous_created_at
        version_item["created_at"] = previous_created_at
        list_item["created_at"] = previous_created_at
    return metadata_item, latest_item, version_item, list_item


def _sanitize_write_items(items):
    sanitized = []
    for item in items:
        sanitized_item = {
            key: stripped
            for key, value in item.items()
            if (stripped := _strip_empty_values(value)) is not None
        }
        sanitized.append(sanitized_item)
    return sanitized


def create_secret(
    tenant_id,
    name,
    secret_pairs,
    created_by,
    metadata=None,
    documentation=None,
    tags=None,
):
    secret_id = str(uuid.uuid4()).replace("-", "")
    revision = 1
    secret_pairs = lowercase_secret_pairs(secret_pairs)
    ok, ret = check_secret_pair_values(secret_pairs)
    if not ok:
        return None, ret
    encrypted_pairs, data_key, cipher_version = _encrypt_secret_pairs(
        tenant_id,
        secret_id,
        secret_pairs,
    )
    now = datetime.now(timezone.utc).isoformat()
    metadata = metadata or {}
    tags = tags or []
    last_decrypted_date = None
    last_rotation_date = now
    secret_keys = list(secret_pairs)
    metadata_item, latest_item, version_item, list_item = _build_secret_items(
        tenant_id,
        secret_id,
        name,
        revision,
        secret_keys,
        encrypted_pairs,
        data_key,
        cipher_version,
        metadata,
        created_by,
        documentation,
        tags,
        last_rotation_date,
        last_decrypted_date,
        now,
    )
    for item in (metadata_item, latest_item, version_item, list_item):
        item["created_at"] = now
        item["updated_at"] = now
    store.put_version_bundle(
        _sanitize_write_items(
            [
                {
                    "Item": metadata_item,
                    "ConditionExpression": "attribute_not_exists(PK)",
                },
                {
                    "Item": latest_item,
                    "ConditionExpression": "attribute_not_exists(PK)",
                },
                {
                    "Item": version_item,
                    "ConditionExpression": "attribute_not_exists(PK)",
                },
                {
                    "Item": list_item,
                    "ConditionExpression": "attribute_not_exists(PK)",
                },
            ]
        )
    )
    return (
        _secret_response_from_item(
            latest_item,
            include_secret_keys=True,
            include_secret_pairs=True,
        ),
        None,
    )


def update_secret(
    tenant_id,
    secret_id,
    name,
    created_by,
    secret_pairs=None,
    metadata=None,
    documentation=None,
    tags=None,
):
    current = store.get_secret_latest(tenant_id, secret_id)
    if not current:
        return None, {"error": "Secret not found."}

    metadata = current.get("metadata", {}) if metadata is None else metadata
    if documentation is None:
        documentation = current.get("documentation")
    if tags is None:
        tags = current.get("tags", [])

    current_secret_pairs = current.get("secret_pairs")
    data_key = current.get("data_key")
    cipher_version = current.get("cipher_version")
    last_decrypted_date = current.get("last_decrypted_date")
    last_rotation_date = current.get("last_rotation_date")

    if secret_pairs is not None:
        secret_pairs = lowercase_secret_pairs(secret_pairs)
        ok, ret = check_secret_pair_values(secret_pairs)
        if not ok:
            return None, ret
        if secret_pairs != _decrypt_secret_pairs(current):
            last_rotation_date = datetime.now(timezone.utc).isoformat()
        encrypted_pairs, data_key, cipher_version = _encrypt_secret_pairs(
            tenant_id,
            secret_id,
            secret_pairs,
        )
    else:
        encrypted_pairs = current_secret_pairs

    revision = int(current["revision"]) + 1
    now = datetime.now(timezone.utc).isoformat()
    secret_keys = (
        list(secret_pairs)
        if secret_pairs is not None
        else current.get("secret_keys", [])
    )
    metadata_item, latest_item, version_item, list_item = _build_secret_items(
        tenant_id,
        secret_id,
        name or current["name"],
        revision,
        secret_keys,
        encrypted_pairs,
        data_key,
        cipher_version,
        metadata,
        created_by,
        documentation,
        tags,
        last_rotation_date,
        last_decrypted_date,
        now,
        previous_created_at=current.get("created_at", current["modified_date"]),
    )
    store.put_version_bundle(
        _sanitize_write_items(
            [
                {
                    "Item": version_item,
                    "ConditionExpression": "attribute_not_exists(PK)",
                },
                {
                    "Item": latest_item,
                    "ConditionExpression": "attribute_exists(PK)",
                },
                {
                    "Item": metadata_item,
                    "ConditionExpression": "revision = :expected",
                    "ExpressionAttributeValues": {
                        ":expected": int(current["revision"]),
                    },
                },
                {
                    "Item": list_item,
                    "ConditionExpression": "attribute_exists(PK)",
                },
            ]
        )
    )
    return (
        _secret_response_from_item(
            latest_item,
            include_secret_keys=True,
            include_secret_pairs=True,
        ),
        None,
    )


def restore_secret_version(
    tenant_id,
    secret_id,
    version,
    created_by,
    comment=None,
):
    current = store.get_secret_latest(tenant_id, secret_id)
    source = store.get_secret_version(tenant_id, secret_id, version)
    if not current or not source:
        return None
    return update_secret(
        tenant_id=tenant_id,
        secret_id=secret_id,
        name=current["name"],
        created_by=created_by,
        secret_pairs=_decrypt_secret_pairs(source),
        metadata=source.get("metadata", {}),
        documentation=source.get("documentation"),
        tags=source.get("tags", []),
    )[0]


def _archive_secret_item(item, tenant_id):
    archived = copy.deepcopy(item)
    archived["PK"] = f"TENANT#{tenant_id}#ARCHIVE_SECRET#{item['id']}"
    return archived


def delete_secret(tenant_id, secret_id):
    current = store.get_secret_latest(tenant_id, secret_id)
    if not current:
        return None, {"error": "Secret not found."}

    dependencies = get_secret_dependencies(tenant_id, secret_id)
    if dependencies:
        return None, {
            "error": "Secret is still mapped to groups.",
            "groups": [group["id"] for group in dependencies],
        }

    if store.get_archive_secret_latest(tenant_id, secret_id):
        store.delete_archive_secret(tenant_id, secret_id)

    versions = store.list_secret_versions(tenant_id, secret_id)
    archived_items = [_archive_secret_item(current, tenant_id)]
    archived_items.extend(
        _archive_secret_item(version, tenant_id) for version in versions
    )
    store.put_archive_secret(tenant_id, secret_id, archived_items)
    store.delete_secret(tenant_id, secret_id)
    return (
        _secret_response_from_item(
            current,
            include_secret_keys=True,
            include_secret_pairs=False,
        ),
        None,
    )


def get_secret_dependencies(tenant_id, secret_id):
    groups = store.list_groups_for_secret(tenant_id, secret_id)
    dependencies = []
    for item in groups:
        dependencies.append(
            {
                "id": item["id"],
            }
        )
    return dependencies
