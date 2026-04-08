import logging
from datetime import datetime
from datetime import timezone

from confidant.schema.groups import GroupResponse
from confidant.schema.groups import GroupsResponse
from confidant.schema.groups import RevisionsResponse
from confidant.services import graphite
from confidant.services.dynamodbstore import store
from confidant.utils import resource_ids

logger = logging.getLogger(__name__)
_SECRET_ACTION_ALIASES = {
    "read": "decrypt",
    "read_with_alert": "decrypt",
}


def _value(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _as_datetime(value):
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def _group_response_from_item(item):
    policies = {}
    raw_policies = item.get("policies", {})
    if not isinstance(raw_policies, dict):
        raw_policies = {}
    for policy_path, allowed_actions in raw_policies.items():
        if not isinstance(allowed_actions, list):
            continue
        normalized_actions = []
        seen = set()
        for action in allowed_actions:
            if not isinstance(action, str):
                continue
            action = _SECRET_ACTION_ALIASES.get(action, action)
            if action in seen:
                continue
            seen.add(action)
            normalized_actions.append(action)
        policies[policy_path] = normalized_actions
    data = {
        "tenant_id": item["tenant_id"],
        "id": item["id"],
        "revision": int(item["revision"]),
        "modified_date": _as_datetime(item["modified_date"]),
        "modified_by": item["modified_by"],
    }
    data["policies"] = policies
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


def get_groups_by_ids(tenant_id, group_ids):
    groups = []
    seen = set()
    for group_id in group_ids:
        if group_id in seen:
            continue
        seen.add(group_id)
        group = get_group_latest(tenant_id, group_id)
        if group is not None:
            groups.append(group)
    return groups


def group_grants_secret_action(group, secret_id, action):
    policies = _value(group, "policies", {})
    if not isinstance(policies, dict):
        return False
    action = _SECRET_ACTION_ALIASES.get(action, action)
    for policy_path, allowed_actions in policies.items():
        normalized_actions = {
            _SECRET_ACTION_ALIASES.get(allowed_action, allowed_action)
            for allowed_action in allowed_actions
            if isinstance(allowed_action, str)
        }
        if (
            resource_ids.secret_policy_matches(policy_path, secret_id)
            and action in normalized_actions
        ):
            return True
    return False


def get_group_map(groups):
    group_map = {}
    for group in groups:
        for secret in _value(group, "policies", {}).keys():
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
        old_secret_ids = list(_value(old_group, "policies", {}).keys())
    else:
        old_secret_ids = []
    new_secret_ids = list(_value(new_group, "policies", {}).keys())
    added = list(set(new_secret_ids) - set(old_secret_ids))
    removed = list(set(old_secret_ids) - set(new_secret_ids))
    msg = "Added secrets: {0}; Removed secrets {1}; Revision {2}"
    msg = msg.format(added, removed, _value(new_group, "revision"))
    graphite.send_event([_value(new_group, "id")], msg)


def get_latest_group_revision(_id, revision):
    return revision + 1


def _build_group_items(
    tenant_id,
    group_id,
    revision,
    policies,
    modified_by,
    created_at,
    previous_created_at=None,
):
    base = {
        "tenant_id": tenant_id,
        "id": group_id,
        "revision": revision,
        "policies": dict(policies),
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
    policies,
    created_by,
):
    revision = 1
    now = datetime.now(timezone.utc).isoformat()
    metadata_item, latest_item, version_item, list_item = _build_group_items(
        tenant_id,
        group_id,
        revision,
        policies,
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
    policies,
    created_by,
):
    current = store.get_group_latest(tenant_id, group_id)
    if not current:
        return None, {"error": "Group not found."}
    current = _group_item_base(current)
    revision = int(current["revision"]) + 1
    now = datetime.now(timezone.utc).isoformat()
    metadata_item, latest_item, version_item, list_item = _build_group_items(
        tenant_id,
        group_id,
        revision,
        policies,
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
        policies=source.get("policies", {}),
        created_by=created_by,
    )[0]


def _archive_group_item(item, tenant_id):
    archived = dict(item)
    archived["PK"] = f"TENANT#{tenant_id}#ARCHIVE_GROUP#{item['id']}"
    return archived


def delete_group(tenant_id, group_id):
    current = store.get_group_latest(tenant_id, group_id)
    if not current:
        return None, {"error": "Group not found."}

    if store.get_archive_group_latest(tenant_id, group_id):
        store.delete_archive_group(tenant_id, group_id)

    versions = store.list_group_versions(tenant_id, group_id)
    archived_items = [_archive_group_item(current, tenant_id)]
    archived_items.extend(
        _archive_group_item(version, tenant_id) for version in versions
    )
    store.put_archive_group(tenant_id, group_id, archived_items)
    store.delete_group(tenant_id, group_id)
    return _group_response_from_item(current), None
