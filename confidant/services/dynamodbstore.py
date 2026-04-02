import base64
import logging
from datetime import datetime
from datetime import timezone
from decimal import Decimal
from typing import Any
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Sequence

import boto3
from boto3.dynamodb.conditions import Attr
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import TypeSerializer
from botocore.exceptions import ClientError

from confidant import settings

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
        normalized = {
            _normalize_map_key(k): normalized_value
            for k, child in value.items()
            if (
                (normalized_key := _normalize_map_key(k)) is not None
                and (normalized_value := _normalize_item_value(child)) is not None
            )
        }
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
    return value


def _serialize_item(item: Dict[str, Any]) -> Dict[str, Any]:
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


def _credential_pk(tenant_id: str, credential_id: str) -> str:
    return f"{_tenant_prefix(tenant_id)}#CREDENTIAL#{credential_id}"


def _credential_list_pk(tenant_id: str) -> str:
    return f"{_tenant_prefix(tenant_id)}#CREDENTIAL_LIST"


def _service_pk(tenant_id: str, service_id: str) -> str:
    return f"{_tenant_prefix(tenant_id)}#SERVICE#{service_id}"


def _service_list_pk(tenant_id: str) -> str:
    return f"{_tenant_prefix(tenant_id)}#SERVICE_LIST"


def _version_sk(version: int) -> str:
    return f"VERSION#{version:010d}"


_SK_METADATA = "#METADATA"
_SK_LATEST = "#LATEST"


def get_boto_resource() -> Any:
    return boto3.resource(
        "dynamodb",
        region_name=settings.AWS_DEFAULT_REGION,
        endpoint_url=settings.DYNAMODB_URL or None,
    )


def _get_table() -> Any:
    return get_boto_resource().Table(settings.DYNAMODB_TABLE)


def _get_client() -> Any:
    return boto3.client(
        "dynamodb",
        region_name=settings.AWS_DEFAULT_REGION,
        endpoint_url=settings.DYNAMODB_URL or None,
    )


def _query_items(
    pk: str,
    *,
    begins_with_sk: Optional[str] = None,
    scan_index_forward: Optional[bool] = None,
    limit: Optional[int] = None,
    last_evaluated_key: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    table = _get_table()
    kwargs: Dict[str, Any] = {
        "KeyConditionExpression": Key("PK").eq(pk),
    }
    if begins_with_sk is not None:
        kwargs["KeyConditionExpression"] = (
            Key("PK").eq(pk) & Key("SK").begins_with(begins_with_sk)
        )
    if scan_index_forward is not None:
        kwargs["ScanIndexForward"] = scan_index_forward
    if limit is not None:
        kwargs["Limit"] = limit
    if last_evaluated_key is not None:
        kwargs["ExclusiveStartKey"] = last_evaluated_key
    return table.query(**kwargs)


def _get_item(pk: str, sk: str) -> Optional[Dict[str, Any]]:
    table = _get_table()
    resp = table.get_item(Key={"PK": pk, "SK": sk})
    return resp.get("Item")


def _transact_put_items(items: Sequence[Dict[str, Any]]) -> None:
    transact_items = []
    for item in items:
        put_item: Dict[str, Any] = {
            "TableName": settings.DYNAMODB_TABLE,
            "Item": _serialize_item(item["Item"]),
        }
        condition = item.get("ConditionExpression")
        if condition:
            put_item["ConditionExpression"] = condition
        expr_values = item.get("ExpressionAttributeValues")
        if expr_values:
            put_item["ExpressionAttributeValues"] = {
                key: _serialize_native(value)
                for key, value in expr_values.items()
            }
        expr_names = item.get("ExpressionAttributeNames")
        if expr_names:
            put_item["ExpressionAttributeNames"] = expr_names
        transact_items.append({"Put": put_item})
    _get_client().transact_write_items(TransactItems=transact_items)


def _update_item(
    key: Dict[str, str],
    *,
    update_expression: str,
    expression_attribute_values: Dict[str, Any],
    expression_attribute_names: Optional[Dict[str, str]] = None,
) -> None:
    table = _get_table()
    kwargs: Dict[str, Any] = {
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

    def list_credentials(
        self,
        tenant_id: str,
        limit: Optional[int] = None,
        last_evaluated_key: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return _query_items(
            _credential_list_pk(tenant_id),
            scan_index_forward=False,
            limit=limit,
            last_evaluated_key=last_evaluated_key,
        )

    def list_services(
        self,
        tenant_id: str,
        limit: Optional[int] = None,
        last_evaluated_key: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return _query_items(
            _service_list_pk(tenant_id),
            scan_index_forward=False,
            limit=limit,
            last_evaluated_key=last_evaluated_key,
        )

    def get_credential_metadata(
        self,
        tenant_id: str,
        credential_id: str,
    ) -> Optional[Dict[str, Any]]:
        return _get_item(_credential_pk(tenant_id, credential_id), _SK_METADATA)

    def get_credential_latest(
        self,
        tenant_id: str,
        credential_id: str,
    ) -> Optional[Dict[str, Any]]:
        return _get_item(_credential_pk(tenant_id, credential_id), _SK_LATEST)

    def get_credential_version(
        self,
        tenant_id: str,
        credential_id: str,
        version: int,
    ) -> Optional[Dict[str, Any]]:
        return _get_item(_credential_pk(tenant_id, credential_id), _version_sk(version))

    def list_credential_versions(
        self,
        tenant_id: str,
        credential_id: str,
    ) -> List[Dict[str, Any]]:
        resp = _query_items(
            _credential_pk(tenant_id, credential_id),
            begins_with_sk="VERSION#",
            scan_index_forward=False,
        )
        return resp.get("Items", [])

    def get_service_metadata(
        self,
        tenant_id: str,
        service_id: str,
    ) -> Optional[Dict[str, Any]]:
        return _get_item(_service_pk(tenant_id, service_id), _SK_METADATA)

    def get_service_latest(
        self,
        tenant_id: str,
        service_id: str,
    ) -> Optional[Dict[str, Any]]:
        return _get_item(_service_pk(tenant_id, service_id), _SK_LATEST)

    def get_service_version(
        self,
        tenant_id: str,
        service_id: str,
        version: int,
    ) -> Optional[Dict[str, Any]]:
        return _get_item(_service_pk(tenant_id, service_id), _version_sk(version))

    def list_service_versions(
        self,
        tenant_id: str,
        service_id: str,
    ) -> List[Dict[str, Any]]:
        resp = _query_items(
            _service_pk(tenant_id, service_id),
            begins_with_sk="VERSION#",
            scan_index_forward=False,
        )
        return resp.get("Items", [])

    def put_version_bundle(
        self,
        items: Sequence[Dict[str, Any]],
    ) -> None:
        _transact_put_items(items)

    def update_credential_last_decrypted_date(
        self,
        tenant_id: str,
        credential_id: str,
        last_decrypted_date: str,
    ) -> None:
        update_expression = "SET #last_decrypted_date = :last_decrypted_date"
        expression_attribute_names = {"#last_decrypted_date": "last_decrypted_date"}
        expression_attribute_values = {
            ":last_decrypted_date": last_decrypted_date,
        }
        keys = [
            {"PK": _credential_pk(tenant_id, credential_id), "SK": _SK_METADATA},
            {"PK": _credential_pk(tenant_id, credential_id), "SK": _SK_LATEST},
            {
                "PK": _credential_list_pk(tenant_id),
                "SK": f"CREDENTIAL#{credential_id}",
            },
        ]
        for key in keys:
            _update_item(
                key,
                update_expression=update_expression,
                expression_attribute_values=expression_attribute_values,
                expression_attribute_names=expression_attribute_names,
            )

    def delete_credential(self, tenant_id: str, credential_id: str) -> None:
        table = _get_table()
        resp = _query_items(
            _credential_pk(tenant_id, credential_id),
            scan_index_forward=False,
        )
        for item in resp.get("Items", []):
            table.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})

        table.delete_item(
            Key={
                "PK": _credential_list_pk(tenant_id),
                "SK": f"CREDENTIAL#{credential_id}",
            }
        )

    def delete_service(self, tenant_id: str, service_id: str) -> None:
        table = _get_table()
        resp = _query_items(
            _service_pk(tenant_id, service_id),
            scan_index_forward=False,
        )
        for item in resp.get("Items", []):
            table.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})

        table.delete_item(
            Key={
                "PK": _service_list_pk(tenant_id),
                "SK": f"SERVICE#{service_id}",
            }
        )

    def list_current_credentials_for_service(
        self,
        tenant_id: str,
        credential_ids: Iterable[str],
    ) -> List[Dict[str, Any]]:
        items = []
        for credential_id in credential_ids:
            item = self.get_credential_latest(tenant_id, credential_id)
            if item:
                items.append(item)
        return items

    def list_services_for_credential(
        self,
        tenant_id: str,
        credential_id: str,
    ) -> List[Dict[str, Any]]:
        resp = self.list_services(tenant_id)
        services = []
        for item in resp.get("Items", []):
            credentials = item.get("credentials", [])
            if credential_id in credentials:
                services.append(item)
        return services

    def scan_service_list_items(self) -> List[Dict[str, Any]]:
        table = _get_table()
        resp = table.scan(
            FilterExpression=Attr("PK").begins_with("TENANT#")
            & Attr("SK").begins_with("SERVICE#"),
        )
        return resp.get("Items", [])


store = DynamoDBConfidantStore()
