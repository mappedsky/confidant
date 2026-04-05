from datetime import datetime
from typing import Any

from pydantic import BaseModel
from pydantic import Field

from confidant.utils.dynamodb import encode_last_evaluated_key


def _value(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class CreateSecretRequest(BaseModel):
    name: str
    secret_pairs: dict[Any, Any]
    metadata: dict[Any, Any] = Field(default_factory=dict)
    enabled: bool = True
    documentation: str | None = None
    tags: list[str] = Field(default_factory=list)


class UpdateSecretRequest(BaseModel):
    name: str | None = None
    secret_pairs: dict[Any, Any] | None = None
    metadata: dict[Any, Any] | None = None
    enabled: bool | None = None
    documentation: str | None = None
    tags: list[str] | None = None


class RestoreSecretVersionRequest(BaseModel):
    comment: str | None = None


class SecretResponse(BaseModel):
    tenant_id: str
    id: str
    name: str
    revision: int
    enabled: bool = True
    modified_date: datetime
    modified_by: str
    documentation: str | None = None
    metadata: dict[Any, Any] = Field(default_factory=dict)
    secret_keys: list[str] = Field(default_factory=list)
    secret_pairs: dict[Any, Any] = Field(default_factory=dict)
    permissions: dict[str, bool] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    last_rotation_date: datetime | None = None
    next_rotation_date: datetime | None = None

    class Config:
        from_attributes = True

    @classmethod
    def from_secret(
        cls,
        secret,
        include_secret_keys=False,
        include_secret_pairs=False,
    ):
        data = {
            "tenant_id": _value(secret, "tenant_id"),
            "id": _value(secret, "id"),
            "name": _value(secret, "name"),
            "revision": _value(secret, "revision"),
            "modified_date": _value(secret, "modified_date"),
            "modified_by": _value(secret, "modified_by"),
        }
        if _value(secret, "enabled") is not None:
            data["enabled"] = _value(secret, "enabled")
        if _value(secret, "metadata") is not None:
            data["metadata"] = _value(secret, "metadata")
        if _value(secret, "documentation") is not None:
            data["documentation"] = _value(secret, "documentation")
        if _value(secret, "tags") is not None:
            data["tags"] = _value(secret, "tags")
        if _value(secret, "last_rotation_date") is not None:
            data["last_rotation_date"] = _value(secret, "last_rotation_date")
        if _value(secret, "next_rotation_date") is not None:
            data["next_rotation_date"] = _value(secret, "next_rotation_date")
        if include_secret_keys:
            data["secret_keys"] = _value(secret, "secret_keys", [])
        if include_secret_pairs:
            decrypted = _value(secret, "decrypted_secret_pairs", None)
            if decrypted is None:
                decrypted = _value(secret, "secret_pairs", {})
            data["secret_pairs"] = decrypted
        return cls(**data)


class SecretsResponse(BaseModel):
    secrets: list[SecretResponse]
    next_page: str | None = None

    @classmethod
    def from_secrets(
        cls,
        secrets,
        next_page=None,
        include_secret_keys=False,
        include_secret_pairs=False,
    ):
        secrets_list = [
            SecretResponse.from_secret(
                secret,
                include_secret_keys,
                include_secret_pairs,
            )
            for secret in secrets
        ]
        secrets_list.sort(key=lambda item: item.name.lower())
        return cls(
            secrets=secrets_list,
            next_page=encode_last_evaluated_key(next_page),
        )


class RevisionsResponse(BaseModel):
    versions: list[SecretResponse]
    next_page: str | None = None

    @classmethod
    def from_secrets(
        cls,
        secrets,
        next_page=None,
        include_secret_keys=False,
        include_secret_pairs=False,
    ):
        revisions_list = [
            SecretResponse.from_secret(
                secret,
                include_secret_keys,
                include_secret_pairs,
            )
            for secret in secrets
        ]
        revisions_list.sort(key=lambda item: item.revision)
        return cls(
            versions=revisions_list,
            next_page=encode_last_evaluated_key(next_page),
        )


class SchemaWrapper:
    def __init__(self, model_cls):
        self.model_cls = model_cls

    def dumps(self, obj):
        if isinstance(obj, self.model_cls):
            return obj.model_dump_json()
        return self.model_cls.model_validate(obj).model_dump_json()


secret_response_schema = SchemaWrapper(SecretResponse)
secrets_response_schema = SchemaWrapper(SecretsResponse)
revisions_response_schema = SchemaWrapper(RevisionsResponse)
secret_version_list_response_schema = revisions_response_schema

SecretResponseSchema = SchemaWrapper
SecretsResponseSchema = SchemaWrapper
RevisionsResponseSchema = SchemaWrapper
SecretVersionListResponseSchema = SchemaWrapper
