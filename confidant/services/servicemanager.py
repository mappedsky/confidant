import logging
from datetime import datetime
from datetime import timezone

from confidant.schema.services import ServiceResponse
from confidant.schema.services import ServicesResponse
from confidant.schema.services import RevisionsResponse
from confidant.services import graphite
from confidant.services.dynamodbstore import store
from confidant.utils import stats

logger = logging.getLogger(__name__)


def _value(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _as_datetime(value):
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def _service_response_from_item(item):
    data = {
        "tenant_id": item["tenant_id"],
        "id": item["id"],
        "revision": int(item["revision"]),
        "modified_date": _as_datetime(item["modified_date"]),
        "modified_by": item["modified_by"],
    }
    if item.get("enabled") is not None:
        data["enabled"] = item["enabled"]
    data["credentials"] = item.get("credentials", [])
    return ServiceResponse(**data)


def _service_item_base(item):
    return {
        key: value
        for key, value in item.items()
        if key != "account"
    }


def list_services(tenant_id, limit=None, page=None):
    results = store.list_services(
        tenant_id,
        limit=limit,
        last_evaluated_key=page,
    )
    services = [
        _service_response_from_item(item)
        for item in results.get("Items", [])
    ]
    return ServicesResponse.from_services(
        services,
        next_page=results.get("LastEvaluatedKey"),
    )


def get_service_latest(tenant_id, service_id):
    item = store.get_service_latest(tenant_id, service_id)
    if not item:
        return None
    return _service_response_from_item(
        item,
    )


def list_service_versions(tenant_id, service_id):
    items = store.list_service_versions(tenant_id, service_id)
    services = [
        _service_response_from_item(item)
        for item in items
    ]
    return RevisionsResponse.from_services(services)


def get_service_version(tenant_id, service_id, version):
    item = store.get_service_version(tenant_id, service_id, version)
    if not item:
        return None
    return _service_response_from_item(item)


def get_services_for_credential(tenant_id, credential_id):
    services = store.list_services_for_credential(tenant_id, credential_id)
    return [item["id"] for item in services]


def get_service_map(services):
    service_map = {}
    for service in services:
        for credential in _value(service, "credentials", []):
            if credential in service_map:
                service_map[credential]["service_ids"].append(_value(service, "id"))
            else:
                service_map[credential] = {
                    "data_type": "credential",
                    "service_ids": [_value(service, "id")],
                }
    return service_map


def send_service_mapping_graphite_event(new_service, old_service):
    if old_service:
        old_credential_ids = _value(old_service, "credentials", [])
    else:
        old_credential_ids = []
    added = list(set(_value(new_service, "credentials", [])) - set(old_credential_ids))
    removed = list(set(old_credential_ids) - set(_value(new_service, "credentials", [])))
    msg = "Added credentials: {0}; Removed credentials {1}; Revision {2}"
    msg = msg.format(added, removed, _value(new_service, "revision"))
    graphite.send_event([_value(new_service, "id")], msg)


def get_latest_service_revision(_id, revision):
    return revision + 1


def _build_service_items(
    tenant_id,
    service_id,
    revision,
    credentials,
    enabled,
    modified_by,
    created_at,
    previous_created_at=None,
):
    base = {
        "tenant_id": tenant_id,
        "id": service_id,
        "revision": revision,
        "credentials": list(credentials),
        "enabled": enabled,
        "modified_date": created_at,
        "modified_by": modified_by,
    }
    metadata_item = {
        "PK": f"TENANT#{tenant_id}#SERVICE#{service_id}",
        "SK": "#METADATA",
        **base,
    }
    latest_item = {
        "PK": f"TENANT#{tenant_id}#SERVICE#{service_id}",
        "SK": "#LATEST",
        **base,
    }
    version_item = {
        "PK": f"TENANT#{tenant_id}#SERVICE#{service_id}",
        "SK": f"VERSION#{revision:010d}",
        **base,
    }
    list_item = {
        "PK": f"TENANT#{tenant_id}#SERVICE_LIST",
        "SK": f"SERVICE#{service_id}",
        **base,
    }
    if previous_created_at is not None:
        metadata_item["created_at"] = previous_created_at
        latest_item["created_at"] = previous_created_at
        version_item["created_at"] = previous_created_at
        list_item["created_at"] = previous_created_at
    return metadata_item, latest_item, version_item, list_item


def create_service(
    tenant_id,
    service_id,
    credentials,
    created_by,
    enabled=True,
):
    revision = 1
    now = datetime.now(timezone.utc).isoformat()
    metadata_item, latest_item, version_item, list_item = _build_service_items(
        tenant_id,
        service_id,
        revision,
        credentials,
        enabled,
        created_by,
        now,
    )
    for item in (metadata_item, latest_item, version_item, list_item):
        item["created_at"] = now
        item["updated_at"] = now
    store.put_version_bundle(
        [
            {"Item": metadata_item, "ConditionExpression": "attribute_not_exists(PK)"},
            {"Item": latest_item, "ConditionExpression": "attribute_not_exists(PK)"},
            {"Item": version_item, "ConditionExpression": "attribute_not_exists(PK)"},
            {"Item": list_item, "ConditionExpression": "attribute_not_exists(PK)"},
        ]
    )
    return _service_response_from_item(
        latest_item,
    ), None


def update_service(
    tenant_id,
    service_id,
    credentials,
    created_by,
    enabled=None,
):
    current = store.get_service_latest(tenant_id, service_id)
    if not current:
        return None, {"error": "Service not found."}
    current = _service_item_base(current)
    if enabled is None:
        enabled = current.get("enabled", True)
    revision = int(current["revision"]) + 1
    now = datetime.now(timezone.utc).isoformat()
    metadata_item, latest_item, version_item, list_item = _build_service_items(
        tenant_id,
        service_id,
        revision,
        credentials,
        enabled,
        created_by,
        now,
        previous_created_at=current.get("created_at", current["modified_date"]),
    )
    store.put_version_bundle(
        [
            {"Item": version_item, "ConditionExpression": "attribute_not_exists(PK)"},
            {"Item": latest_item, "ConditionExpression": "attribute_exists(PK)"},
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
    return _service_response_from_item(
        latest_item,
    ), None


def restore_service_version(
    tenant_id,
    service_id,
    version,
    created_by,
    comment=None,
):
    current = store.get_service_latest(tenant_id, service_id)
    source = store.get_service_version(tenant_id, service_id, version)
    if not current or not source:
        return None
    source = _service_item_base(source)
    return update_service(
        tenant_id=tenant_id,
        service_id=service_id,
        credentials=source.get("credentials", []),
        created_by=created_by,
        enabled=source.get("enabled", True),
    )[0]
