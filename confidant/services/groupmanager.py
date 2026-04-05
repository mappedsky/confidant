import logging
from datetime import datetime
from datetime import timezone

from confidant.schema.groups import GroupResponse
from confidant.schema.groups import GroupsResponse
from confidant.schema.groups import RevisionsResponse
from confidant.services import graphite
from confidant.services.dynamodbstore import store

logger = logging.getLogger(__name__)


def _value(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _as_datetime(value):
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def _group_response_from_item(item):
    data = {
        "tenant_id": item["tenant_id"],
        "id": item["id"],
        "revision": int(item["revision"]),
        "modified_date": _as_datetime(item["modified_date"]),
        "modified_by": item["modified_by"],
    }
    if item.get("enabled") is not None:
        data["enabled"] = item["enabled"]
    data["secrets"] = item.get("secrets", [])
    return GroupResponse(**data)


def _group_item_base(item):
    return {key: value for key, value in item.items() if key != "account"}


def list_groups(tenant_id, limit=None, page=None):
    results = store.list_groups(
        tenant_id,
        limit=limit,
        last_evaluated_key=page,
    )
    items = results.get("Items", [])
    groups = [_group_response_from_item(item) for item in items]
    return GroupsResponse.from_groups(
        groups,
        next_page=results.get("LastEvaluatedKey"),
    )


def get_group_latest(tenant_id, group_id):
    item = store.get_group_latest(tenant_id, group_id)
    if not item:
        return None
    return _group_response_from_item(
        item,
    )


def list_group_versions(tenant_id, group_id):
    items = store.list_group_versions(tenant_id, group_id)
    groups = [_group_response_from_item(item) for item in items]
    return RevisionsResponse.from_groups(groups)


def get_group_version(tenant_id, group_id, version):
    item = store.get_group_version(tenant_id, group_id, version)
    if not item:
        return None
    return _group_response_from_item(item)


def get_groups_for_secret(tenant_id, secret_id):
    groups = store.list_groups_for_secret(tenant_id, secret_id)
    return [item["id"] for item in groups]


def get_group_map(groups):
    group_map = {}
    for group in groups:
        for secret in _value(group, "secrets", []):
            if secret in group_map:
                group_map[secret]["group_ids"].append(_value(group, "id"))
            else:
                group_map[secret] = {
                    "data_type": "secret",
                    "group_ids": [_value(group, "id")],
                }
    return group_map


def send_group_mapping_graphite_event(new_group, old_group):
    if old_group:
        old_secret_ids = _value(old_group, "secrets", [])
    else:
        old_secret_ids = []
    added = list(set(_value(new_group, "secrets", [])) - set(old_secret_ids))
    removed = list(set(old_secret_ids) - set(_value(new_group, "secrets", [])))
    msg = "Added secrets: {0}; Removed secrets {1}; Revision {2}"
    msg = msg.format(added, removed, _value(new_group, "revision"))
    graphite.send_event([_value(new_group, "id")], msg)


def get_latest_group_revision(_id, revision):
    return revision + 1


def _build_group_items(
    tenant_id,
    group_id,
    revision,
    secrets,
    enabled,
    modified_by,
    created_at,
    previous_created_at=None,
):
    base = {
        "tenant_id": tenant_id,
        "id": group_id,
        "revision": revision,
        "secrets": list(secrets),
        "enabled": enabled,
        "modified_date": created_at,
        "modified_by": modified_by,
    }
    metadata_item = {
        "PK": f"TENANT#{tenant_id}#GROUP#{group_id}",
        "SK": "#METADATA",
        **base,
    }
    latest_item = {
        "PK": f"TENANT#{tenant_id}#GROUP#{group_id}",
        "SK": "#LATEST",
        **base,
    }
    version_item = {
        "PK": f"TENANT#{tenant_id}#GROUP#{group_id}",
        "SK": f"VERSION#{revision:010d}",
        **base,
    }
    list_item = {
        "PK": f"TENANT#{tenant_id}#GROUP_LIST",
        "SK": f"GROUP#{group_id}",
        **base,
    }
    if previous_created_at is not None:
        metadata_item["created_at"] = previous_created_at
        latest_item["created_at"] = previous_created_at
        version_item["created_at"] = previous_created_at
        list_item["created_at"] = previous_created_at
    return metadata_item, latest_item, version_item, list_item


def create_group(
    tenant_id,
    group_id,
    secrets,
    created_by,
    enabled=True,
):
    revision = 1
    now = datetime.now(timezone.utc).isoformat()
    metadata_item, latest_item, version_item, list_item = _build_group_items(
        tenant_id,
        group_id,
        revision,
        secrets,
        enabled,
        created_by,
        now,
    )
    for item in (metadata_item, latest_item, version_item, list_item):
        item["created_at"] = now
        item["updated_at"] = now
    store.put_version_bundle(
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
    return (
        _group_response_from_item(
            latest_item,
        ),
        None,
    )


def update_group(
    tenant_id,
    group_id,
    secrets,
    created_by,
    enabled=None,
):
    current = store.get_group_latest(tenant_id, group_id)
    if not current:
        return None, {"error": "Group not found."}
    current = _group_item_base(current)
    if enabled is None:
        enabled = current.get("enabled", True)
    revision = int(current["revision"]) + 1
    now = datetime.now(timezone.utc).isoformat()
    metadata_item, latest_item, version_item, list_item = _build_group_items(
        tenant_id,
        group_id,
        revision,
        secrets,
        enabled,
        created_by,
        now,
        previous_created_at=current.get("created_at", current["modified_date"]),
    )
    store.put_version_bundle(
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
            {"Item": list_item, "ConditionExpression": "attribute_exists(PK)"},
        ]
    )
    return (
        _group_response_from_item(
            latest_item,
        ),
        None,
    )


def restore_group_version(
    tenant_id,
    group_id,
    version,
    created_by,
    comment=None,
):
    current = store.get_group_latest(tenant_id, group_id)
    source = store.get_group_version(tenant_id, group_id, version)
    if not current or not source:
        return None
    source = _group_item_base(source)
    return update_group(
        tenant_id=tenant_id,
        group_id=group_id,
        secrets=source.get("secrets", []),
        created_by=created_by,
        enabled=source.get("enabled", True),
    )[0]
