import base64
import logging
from collections.abc import Iterable
from collections.abc import Sequence
from datetime import datetime
from datetime import timezone
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Attr
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import TypeSerializer
from botocore.config import Config

from confidant import settings
from confidant.utils import resource_ids

logger = logging.getLogger(__name__)

_serializer = TypeSerializer()


def _is_empty_value(value: Any) -> bool:
    if value is None:
        return True
    if value == "":
        return True
    if isinstance(value, (list, tuple, set, frozenset, dict)):
        return len(value) == 0
    if isinstance(value, (bytes, bytearray)):
        return len(value) == 0
    return False


def _normalize_item_value(value: Any) -> Any:
    if _is_empty_value(value):
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, (bytes, bytearray)):
        return base64.b64encode(bytes(value)).decode("UTF-8")
    if isinstance(value, dict):
        normalized = {}
        for key, child in value.items():
            normalized_key = _normalize_map_key(key)
            normalized_value = _normalize_item_value(child)
            if normalized_key is None or normalized_value is None:
                continue
            normalized[normalized_key] = normalized_value
        return normalized or None
    if isinstance(value, list):
        normalized = [
            normalized_value
            for child in value
            if (normalized_value := _normalize_item_value(child)) is not None
        ]
        return normalized or None
    if isinstance(value, tuple):
        normalized = [
            normalized_value
            for child in value
            if (normalized_value := _normalize_item_value(child)) is not None
        ]
        return normalized or None
    if isinstance(value, (set, frozenset)):
        normalized = {
            normalized_value
            for child in value
            if (normalized_value := _normalize_item_value(child)) is not None
        }
        return normalized or None
    if isinstance(value, (str, bool, int, Decimal)):
        return value
    return str(value)


def _normalize_map_key(key: Any) -> Any:
    if isinstance(key, str):
        key = key.strip()
        return key or None
    if key is None:
        return None
    return str(key)


def _serialize_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        key: _serializer.serialize(_normalize_item_value(value))
        for key, value in item.items()
        if _normalize_item_value(value) is not None
    }


def _serialize_native(value: Any) -> Any:
    return _serializer.serialize(_normalize_item_value(value))


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _tenant_prefix(tenant_id: str) -> str:
    return f"TENANT#{tenant_id}"


def _secret_pk(tenant_id: str, secret_id: str) -> str:
    return f"{_tenant_prefix(tenant_id)}#SECRET#{secret_id}"


def _secret_list_pk(tenant_id: str) -> str:
    return f"{_tenant_prefix(tenant_id)}#SECRET_LIST"


def _archive_secret_pk(tenant_id: str, secret_id: str) -> str:
    return f"{_tenant_prefix(tenant_id)}#ARCHIVE_SECRET#{secret_id}"


def _archive_secret_list_pk(tenant_id: str) -> str:
    return f"{_tenant_prefix(tenant_id)}#ARCHIVE_SECRET_LIST"


def _group_pk(tenant_id: str, group_id: str) -> str:
    return f"{_tenant_prefix(tenant_id)}#GROUP#{group_id}"


def _group_list_pk(tenant_id: str) -> str:
    return f"{_tenant_prefix(tenant_id)}#GROUP_LIST"


def _archive_group_pk(tenant_id: str, group_id: str) -> str:
    return f"{_tenant_prefix(tenant_id)}#ARCHIVE_GROUP#{group_id}"


def _archive_group_list_pk(tenant_id: str) -> str:
    return f"{_tenant_prefix(tenant_id)}#ARCHIVE_GROUP_LIST"


def _version_sk(version: int) -> str:
    return f"VERSION#{version:010d}"


_SK_METADATA = "#METADATA"
_SK_LATEST = "#LATEST"


def get_boto_resource() -> Any:
    return boto3.resource(
        "dynamodb",
        region_name=settings.AWS_DEFAULT_REGION,
        endpoint_url=settings.DYNAMODB_URL or None,
        config=Config(
            connect_timeout=settings.DYNAMODB_CONNECT_TIMEOUT_SECONDS,
            read_timeout=settings.DYNAMODB_READ_TIMEOUT_SECONDS,
            max_pool_connections=settings.DYNAMODB_CONNECTION_POOL_SIZE,
        ),
    )


def _get_table() -> Any:
    return get_boto_resource().Table(settings.DYNAMODB_TABLE)


def _get_client() -> Any:
    return boto3.client(
        "dynamodb",
        region_name=settings.AWS_DEFAULT_REGION,
        endpoint_url=settings.DYNAMODB_URL or None,
        config=Config(
            connect_timeout=settings.DYNAMODB_CONNECT_TIMEOUT_SECONDS,
            read_timeout=settings.DYNAMODB_READ_TIMEOUT_SECONDS,
            max_pool_connections=settings.DYNAMODB_CONNECTION_POOL_SIZE,
        ),
    )


def _query_items(
    pk: str,
    *,
    begins_with_sk: str | None = None,
    scan_index_forward: bool | None = None,
    limit: int | None = None,
    last_evaluated_key: dict[str, Any] | None = None,
) -> dict[str, Any]:
    table = _get_table()
    kwargs: dict[str, Any] = {
        "KeyConditionExpression": Key("PK").eq(pk),
    }
    if begins_with_sk is not None:
        key_condition = Key("PK").eq(pk) & Key("SK").begins_with(begins_with_sk)
        kwargs["KeyConditionExpression"] = key_condition
    if scan_index_forward is not None:
        kwargs["ScanIndexForward"] = scan_index_forward
    if limit is not None:
        kwargs["Limit"] = limit
    if last_evaluated_key is not None:
        kwargs["ExclusiveStartKey"] = last_evaluated_key
    return table.query(**kwargs)


def _get_item(pk: str, sk: str) -> dict[str, Any] | None:
    table = _get_table()
    resp = table.get_item(Key={"PK": pk, "SK": sk})
    return resp.get("Item")


def _batch_put_items(items: Sequence[dict[str, Any]]) -> None:
    table = _get_table()
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=_normalize_item_value(item))


def _transact_put_items(items: Sequence[dict[str, Any]]) -> None:
    transact_items = []
    for item in items:
        put_item: dict[str, Any] = {
            "TableName": settings.DYNAMODB_TABLE,
            "Item": _serialize_item(item["Item"]),
        }
        condition = item.get("ConditionExpression")
        if condition:
            put_item["ConditionExpression"] = condition
        expr_values = item.get("ExpressionAttributeValues")
        if expr_values:
            serialized_values = {}
            for key, value in expr_values.items():
                serialized_values[key] = _serialize_native(value)
            put_item["ExpressionAttributeValues"] = serialized_values
        expr_names = item.get("ExpressionAttributeNames")
        if expr_names:
            put_item["ExpressionAttributeNames"] = expr_names
        transact_items.append({"Put": put_item})
    _get_client().transact_write_items(TransactItems=transact_items)


def _update_item(
    key: dict[str, str],
    *,
    update_expression: str,
    expression_attribute_values: dict[str, Any],
    expression_attribute_names: dict[str, str] | None = None,
) -> None:
    table = _get_table()
    kwargs: dict[str, Any] = {
        "Key": key,
        "UpdateExpression": update_expression,
        "ExpressionAttributeValues": expression_attribute_values,
    }
    if expression_attribute_names:
        kwargs["ExpressionAttributeNames"] = expression_attribute_names
    table.update_item(**kwargs)


class DynamoDBConfidantStore:
    def initialize(self) -> None:
        table_name = settings.DYNAMODB_TABLE
        resource = get_boto_resource()
        existing_names = {t.name for t in resource.tables.all()}
        if table_name in existing_names:
            return
        try:
            resource.create_table(
                TableName=table_name,
                KeySchema=[
                    {"AttributeName": "PK", "KeyType": "HASH"},
                    {"AttributeName": "SK", "KeyType": "RANGE"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "PK", "AttributeType": "S"},
                    {"AttributeName": "SK", "AttributeType": "S"},
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            logger.info("Created DynamoDB table", extra={"table": table_name})
        except resource.meta.client.exceptions.ResourceInUseException:
            logger.info(
                "DynamoDB table already exists (created by another worker)",
                extra={"table": table_name},
            )

    def list_secrets(
        self,
        tenant_id: str,
        limit: int | None = None,
        last_evaluated_key: dict[str, Any] | None = None,
        prefix: str | None = None,
    ) -> dict[str, Any]:
        query_kwargs = {
            "scan_index_forward": False,
            "limit": limit,
            "last_evaluated_key": last_evaluated_key,
        }
        if prefix:
            query_kwargs["begins_with_sk"] = prefix
        return _query_items(
            _secret_list_pk(tenant_id),
            **query_kwargs,
        )

    def list_groups(
        self,
        tenant_id: str,
        limit: int | None = None,
        last_evaluated_key: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return _query_items(
            _group_list_pk(tenant_id),
            scan_index_forward=False,
            limit=limit,
            last_evaluated_key=last_evaluated_key,
        )

    def get_secret_metadata(
        self,
        tenant_id: str,
        secret_id: str,
    ) -> dict[str, Any] | None:
        return _get_item(_secret_pk(tenant_id, secret_id), _SK_METADATA)

    def get_secret_latest(
        self,
        tenant_id: str,
        secret_id: str,
    ) -> dict[str, Any] | None:
        return _get_item(_secret_pk(tenant_id, secret_id), _SK_LATEST)

    def get_secret_version(
        self,
        tenant_id: str,
        secret_id: str,
        version: int,
    ) -> dict[str, Any] | None:
        return _get_item(_secret_pk(tenant_id, secret_id), _version_sk(version))

    def list_secret_versions(
        self,
        tenant_id: str,
        secret_id: str,
    ) -> list[dict[str, Any]]:
        resp = _query_items(
            _secret_pk(tenant_id, secret_id),
            begins_with_sk="VERSION#",
            scan_index_forward=False,
        )
        return resp.get("Items", [])

    def get_archive_secret_latest(
        self,
        tenant_id: str,
        secret_id: str,
    ) -> dict[str, Any] | None:
        return _get_item(_archive_secret_pk(tenant_id, secret_id), _SK_LATEST)

    def get_archive_secret_version(
        self,
        tenant_id: str,
        secret_id: str,
        version: int,
    ) -> dict[str, Any] | None:
        return _get_item(
            _archive_secret_pk(tenant_id, secret_id),
            _version_sk(version),
        )

    def list_archive_secret_versions(
        self,
        tenant_id: str,
        secret_id: str,
    ) -> list[dict[str, Any]]:
        resp = _query_items(
            _archive_secret_pk(tenant_id, secret_id),
            begins_with_sk="VERSION#",
            scan_index_forward=False,
        )
        return resp.get("Items", [])

    def list_archive_secrets(
        self,
        tenant_id: str,
        limit: int | None = None,
        last_evaluated_key: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return _query_items(
            _archive_secret_list_pk(tenant_id),
            scan_index_forward=False,
            limit=limit,
            last_evaluated_key=last_evaluated_key,
        )

    def get_group_metadata(
        self,
        tenant_id: str,
        group_id: str,
    ) -> dict[str, Any] | None:
        return _get_item(_group_pk(tenant_id, group_id), _SK_METADATA)

    def get_group_latest(
        self,
        tenant_id: str,
        group_id: str,
    ) -> dict[str, Any] | None:
        return _get_item(_group_pk(tenant_id, group_id), _SK_LATEST)

    def get_group_version(
        self,
        tenant_id: str,
        group_id: str,
        version: int,
    ) -> dict[str, Any] | None:
        return _get_item(_group_pk(tenant_id, group_id), _version_sk(version))

    def list_group_versions(
        self,
        tenant_id: str,
        group_id: str,
    ) -> list[dict[str, Any]]:
        resp = _query_items(
            _group_pk(tenant_id, group_id),
            begins_with_sk="VERSION#",
            scan_index_forward=False,
        )
        return resp.get("Items", [])

    def get_archive_group_latest(
        self,
        tenant_id: str,
        group_id: str,
    ) -> dict[str, Any] | None:
        return _get_item(_archive_group_pk(tenant_id, group_id), _SK_LATEST)

    def list_archive_group_versions(
        self,
        tenant_id: str,
        group_id: str,
    ) -> list[dict[str, Any]]:
        resp = _query_items(
            _archive_group_pk(tenant_id, group_id),
            begins_with_sk="VERSION#",
            scan_index_forward=False,
        )
        return resp.get("Items", [])

    def put_version_bundle(
        self,
        items: Sequence[dict[str, Any]],
    ) -> None:
        _transact_put_items(items)

    def batch_put_items(self, items: Sequence[dict[str, Any]]) -> None:
        _batch_put_items(items)

    def delete_secret(self, tenant_id: str, secret_id: str) -> None:
        table = _get_table()
        resp = _query_items(
            _secret_pk(tenant_id, secret_id),
            scan_index_forward=False,
        )
        for item in resp.get("Items", []):
            table.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})

        table.delete_item(
            Key={
                "PK": _secret_list_pk(tenant_id),
                "SK": secret_id,
            }
        )

    def put_archive_secret(
        self,
        tenant_id: str,
        secret_id: str,
        items: Sequence[dict[str, Any]],
    ) -> None:
        _batch_put_items(
            [
                *items,
                {
                    "PK": _archive_secret_list_pk(tenant_id),
                    "SK": secret_id,
                    "tenant_id": tenant_id,
                    "id": secret_id,
                    "revision": items[0]["revision"],
                    "name": items[0]["name"],
                    "modified_date": items[0]["modified_date"],
                    "modified_by": items[0]["modified_by"],
                    "documentation": items[0].get("documentation"),
                    "metadata": items[0].get("metadata"),
                    "secret_keys": items[0].get("secret_keys"),
                    "created_at": items[0].get("created_at"),
                    "updated_at": _now(),
                },
            ]
        )

    def delete_archive_secret(self, tenant_id: str, secret_id: str) -> None:
        table = _get_table()
        resp = _query_items(
            _archive_secret_pk(tenant_id, secret_id),
            scan_index_forward=False,
        )
        for item in resp.get("Items", []):
            table.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})

        table.delete_item(
            Key={
                "PK": _archive_secret_list_pk(tenant_id),
                "SK": secret_id,
            }
        )

    def delete_group(self, tenant_id: str, group_id: str) -> None:
        table = _get_table()
        resp = _query_items(
            _group_pk(tenant_id, group_id),
            scan_index_forward=False,
        )
        for item in resp.get("Items", []):
            table.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})

        table.delete_item(
            Key={
                "PK": _group_list_pk(tenant_id),
                "SK": f"GROUP#{group_id}",
            }
        )

    def put_archive_group(
        self,
        tenant_id: str,
        group_id: str,
        items: Sequence[dict[str, Any]],
    ) -> None:
        _batch_put_items(
            [
                *items,
                {
                    "PK": _archive_group_list_pk(tenant_id),
                    "SK": f"GROUP#{group_id}",
                    "tenant_id": tenant_id,
                    "id": group_id,
                    "revision": items[0]["revision"],
                    "policies": items[0].get("policies", {}),
                    "modified_date": items[0]["modified_date"],
                    "modified_by": items[0]["modified_by"],
                    "created_at": items[0].get("created_at"),
                    "updated_at": _now(),
                },
            ]
        )

    def delete_archive_group(self, tenant_id: str, group_id: str) -> None:
        table = _get_table()
        resp = _query_items(
            _archive_group_pk(tenant_id, group_id),
            scan_index_forward=False,
        )
        for item in resp.get("Items", []):
            table.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})

        table.delete_item(
            Key={
                "PK": _archive_group_list_pk(tenant_id),
                "SK": f"GROUP#{group_id}",
            }
        )

    def list_current_secrets_for_group(
        self,
        tenant_id: str,
        secret_ids: Iterable[str],
    ) -> list[dict[str, Any]]:
        items = []
        for secret_id in secret_ids:
            item = self.get_secret_latest(tenant_id, secret_id)
            if item:
                items.append(item)
        return items

    def list_groups_for_secret(
        self,
        tenant_id: str,
        secret_id: str,
    ) -> list[dict[str, Any]]:
        resp = self.list_groups(tenant_id)
        groups = []
        for item in resp.get("Items", []):
            policies = item.get("policies", {})
            if any(
                resource_ids.secret_policy_matches(policy_path, secret_id)
                for policy_path in policies
            ):
                groups.append(item)
        return groups

    def scan_group_list_items(self) -> list[dict[str, Any]]:
        table = _get_table()
        resp = table.scan(
            FilterExpression=Attr("PK").begins_with("TENANT#")
            & Attr("SK").begins_with("GROUP#"),
        )
        return resp.get("Items", [])


store = DynamoDBConfidantStore()
