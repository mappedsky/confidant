import copy
import base64
import json
import logging
import re
import uuid
from datetime import datetime
from datetime import timedelta
from datetime import timezone

from confidant import settings
from confidant.schema.credentials import CredentialResponse
from confidant.schema.credentials import CredentialsResponse
from confidant.schema.credentials import RevisionsResponse
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


def _credential_response_from_item(
    item,
    include_credential_keys=False,
    include_credential_pairs=False,
):
    data = {
        "tenant_id": item["tenant_id"],
        "id": item["id"],
        "name": item["name"],
        "revision": int(item["revision"]),
        "modified_date": _as_datetime(item["modified_date"]),
        "modified_by": item["modified_by"],
    }
    if item.get("enabled") is not None:
        data["enabled"] = item["enabled"]
    if item.get("metadata") is not None:
        data["metadata"] = item["metadata"]
    if item.get("documentation") is not None:
        data["documentation"] = item["documentation"]
    if item.get("tags") is not None:
        data["tags"] = item["tags"]
    if item.get("last_rotation_date") is not None:
        data["last_rotation_date"] = _as_datetime(item["last_rotation_date"])
    data["next_rotation_date"] = _next_rotation_date(item)

    if include_credential_keys:
        data["credential_keys"] = item.get("credential_keys", [])
    if include_credential_pairs:
        data["credential_pairs"] = _decrypt_credential_pairs(item)
    return CredentialResponse(**data)


def _decrypt_credential_pairs(item):
    if not item.get("credential_pairs"):
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
    decrypted = cipher.decrypt(item["credential_pairs"])
    return json.loads(decrypted)


def _encrypt_credential_pairs(tenant_id, credential_id, credential_pairs):
    data_key = keymanager.create_datakey(
        encryption_context={"id": credential_id, "tenant_id": tenant_id}
    )
    cipher = CipherManager(data_key["plaintext"], version=2)
    encrypted_pairs = cipher.encrypt(json.dumps(credential_pairs))
    if isinstance(data_key["ciphertext"], bytes):
        data_key = base64.b64encode(data_key["ciphertext"]).decode("UTF-8")
    else:
        data_key = data_key["ciphertext"]
    return encrypted_pairs, data_key, 2


def get_credentials(
    tenant_id,
    credential_ids,
    include_credential_keys=False,
    include_credential_pairs=False,
):
    with stats.timer("service_batch_get_credentials"):
        _credential_ids = copy.deepcopy(credential_ids)
        credentials = []
        for credential_id in _credential_ids:
            item = store.get_credential_latest(tenant_id, credential_id)
            if item:
                credentials.append(
                    _credential_response_from_item(
                        item,
                        include_credential_keys=include_credential_keys,
                        include_credential_pairs=include_credential_pairs,
                    )
                )
        return credentials


def list_credentials(tenant_id, limit=None, page=None):
    results = store.list_credentials(
        tenant_id,
        limit=limit,
        last_evaluated_key=page,
    )
    credentials = [
        _credential_response_from_item(item)
        for item in results.get("Items", [])
    ]
    return CredentialsResponse.from_credentials(
        credentials,
        next_page=results.get("LastEvaluatedKey"),
    )


def get_credential_latest(tenant_id, credential_id, metadata_only=False):
    item = (
        store.get_credential_metadata(tenant_id, credential_id)
        if metadata_only
        else store.get_credential_latest(tenant_id, credential_id)
    )
    if not item:
        return None
    return _credential_response_from_item(
        item,
        include_credential_keys=True,
        include_credential_pairs=not metadata_only,
    )


def list_credential_versions(tenant_id, credential_id):
    items = store.list_credential_versions(tenant_id, credential_id)
    credentials = [
        _credential_response_from_item(
            item,
            include_credential_keys=True,
            include_credential_pairs=False,
        )
        for item in items
    ]
    return RevisionsResponse.from_credentials(credentials)


def get_credential_version(tenant_id, credential_id, version):
    item = store.get_credential_version(tenant_id, credential_id, version)
    if not item:
        return None
    return _credential_response_from_item(
        item,
        include_credential_keys=True,
        include_credential_pairs=True,
    )


def pair_key_conflicts_for_credentials(tenant_id, credential_ids):
    conflicts = {}
    pair_keys = {}
    if settings.IGNORE_CONFLICTS:
        return conflicts
    credentials = get_credentials(
        tenant_id,
        credential_ids,
        include_credential_keys=True,
    )
    for credential in credentials:
        for key in credential.credential_keys:
            data = {
                "id": credential.id,
                "data_type": "credential",
            }
            if key in pair_keys:
                pair_keys[key].append(data)
            else:
                pair_keys[key] = [data]
    for key, data in pair_keys.items():
        if len(data) > 1:
            ids = [k["id"] for k in data if k["data_type"] == "credential"]
            conflicts[key] = {"credentials": ids}
    return conflicts


def check_credential_pair_values(credential_pairs):
    for key, val in credential_pairs.items():
        if isinstance(val, dict) or isinstance(val, list):
            ret = {"error": "credential pairs must be key: value"}
            return (False, ret)
        if re.search(r"\s", key):
            ret = {"error": "credential key must not contain whitespace"}
            return (False, ret)
    return (True, {})


def lowercase_credential_pairs(credential_pairs):
    return {i.lower(): j for i, j in credential_pairs.items()}


def get_revision_ids_for_credential(credential):
    _range = range(1, credential.revision + 1)
    ids = []
    for i in _range:
        ids.append("{0}-{1}".format(credential.id, i))
    return ids


def get_latest_credential_revision(_id, revision):
    return revision + 1


def _build_credential_items(
    tenant_id,
    credential_id,
    name,
    revision,
    credential_keys,
    credential_pairs,
    data_key,
    cipher_version,
    metadata,
    enabled,
    modified_by,
    documentation,
    tags,
    last_rotation_date,
    created_at,
    previous_created_at=None,
):
    base = {
        "tenant_id": tenant_id,
        "id": credential_id,
        "name": name,
        "revision": revision,
        "enabled": enabled,
        "metadata": metadata,
        "modified_date": created_at,
        "modified_by": modified_by,
        "documentation": documentation,
        "tags": tags,
        "last_rotation_date": last_rotation_date,
        "credential_keys": list(credential_keys),
        "credential_pairs": credential_pairs,
        "data_key": data_key,
        "cipher_version": cipher_version,
    }
    metadata_item = {
        "PK": f"TENANT#{tenant_id}#CREDENTIAL#{credential_id}",
        "SK": "#METADATA",
        **base,
    }
    latest_item = {
        "PK": f"TENANT#{tenant_id}#CREDENTIAL#{credential_id}",
        "SK": "#LATEST",
        **base,
    }
    version_item = {
        "PK": f"TENANT#{tenant_id}#CREDENTIAL#{credential_id}",
        "SK": f"VERSION#{revision:010d}",
        **base,
    }
    list_item = {
        "PK": f"TENANT#{tenant_id}#CREDENTIAL_LIST",
        "SK": f"CREDENTIAL#{credential_id}",
        "tenant_id": tenant_id,
        "id": credential_id,
        "name": name,
        "revision": revision,
        "enabled": enabled,
        "metadata": metadata,
        "modified_date": created_at,
        "modified_by": modified_by,
        "documentation": documentation,
        "tags": tags,
        "last_rotation_date": last_rotation_date,
        "credential_keys": list(credential_keys),
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


def create_credential(
    tenant_id,
    name,
    credential_pairs,
    created_by,
    enabled=True,
    metadata=None,
    documentation=None,
    tags=None,
):
    credential_id = str(uuid.uuid4()).replace("-", "")
    revision = 1
    credential_pairs = lowercase_credential_pairs(credential_pairs)
    ok, ret = check_credential_pair_values(credential_pairs)
    if not ok:
        return None, ret
    encrypted_pairs, data_key, cipher_version = _encrypt_credential_pairs(
        tenant_id,
        credential_id,
        credential_pairs,
    )
    now = datetime.now(timezone.utc).isoformat()
    metadata = metadata or {}
    tags = tags or []
    last_rotation_date = now
    credential_keys = list(credential_pairs)
    metadata_item, latest_item, version_item, list_item = _build_credential_items(
        tenant_id,
        credential_id,
        name,
        revision,
        credential_keys,
        encrypted_pairs,
        data_key,
        cipher_version,
        metadata,
        enabled,
        created_by,
        documentation,
        tags,
        last_rotation_date,
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
    return _credential_response_from_item(
        latest_item,
        include_credential_keys=True,
        include_credential_pairs=True,
    ), None


def update_credential(
    tenant_id,
    credential_id,
    name,
    created_by,
    credential_pairs=None,
    enabled=None,
    metadata=None,
    documentation=None,
    tags=None,
):
    current = store.get_credential_latest(tenant_id, credential_id)
    if not current:
        return None, {"error": "Credential not found."}

    metadata = current.get("metadata", {}) if metadata is None else metadata
    if enabled is None:
        enabled = current.get("enabled", True)
    if documentation is None:
        documentation = current.get("documentation")
    if tags is None:
        tags = current.get("tags", [])

    current_credential_pairs = current.get("credential_pairs")
    data_key = current.get("data_key")
    cipher_version = current.get("cipher_version")
    last_rotation_date = current.get("last_rotation_date")

    if credential_pairs is not None:
        credential_pairs = lowercase_credential_pairs(credential_pairs)
        ok, ret = check_credential_pair_values(credential_pairs)
        if not ok:
            return None, ret
        if credential_pairs != _decrypt_credential_pairs(current):
            last_rotation_date = datetime.now(timezone.utc).isoformat()
        encrypted_pairs, data_key, cipher_version = _encrypt_credential_pairs(
            tenant_id,
            credential_id,
            credential_pairs,
        )
    else:
        encrypted_pairs = current_credential_pairs

    revision = int(current["revision"]) + 1
    now = datetime.now(timezone.utc).isoformat()
    credential_keys = list(credential_pairs) if credential_pairs is not None else current.get("credential_keys", [])
    metadata_item, latest_item, version_item, list_item = _build_credential_items(
        tenant_id,
        credential_id,
        name or current["name"],
        revision,
        credential_keys,
        encrypted_pairs,
        data_key,
        cipher_version,
        metadata,
        enabled,
        created_by,
        documentation,
        tags,
        last_rotation_date,
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
    return _credential_response_from_item(
        latest_item,
        include_credential_keys=True,
        include_credential_pairs=True,
    ), None


def restore_credential_version(
    tenant_id,
    credential_id,
    version,
    created_by,
    comment=None,
):
    current = store.get_credential_latest(tenant_id, credential_id)
    source = store.get_credential_version(tenant_id, credential_id, version)
    if not current or not source:
        return None
    return update_credential(
        tenant_id=tenant_id,
        credential_id=credential_id,
        name=current["name"],
        created_by=created_by,
        credential_pairs=_decrypt_credential_pairs(source),
        enabled=source.get("enabled", True),
        metadata=source.get("metadata", {}),
        documentation=source.get("documentation"),
        tags=source.get("tags", []),
    )[0]


def get_credential_dependencies(tenant_id, credential_id):
    services = store.list_services_for_credential(tenant_id, credential_id)
    _services = [{"id": x["id"], "enabled": x.get("enabled", True)} for x in services]
    return _services
