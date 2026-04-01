from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from confidant.utils.dynamodb import encode_last_evaluated_key


def _value(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class CreateCredentialRequest(BaseModel):
    name: str
    credential_pairs: Dict[Any, Any]
    metadata: Dict[Any, Any] = Field(default_factory=dict)
    enabled: bool = True
    documentation: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class UpdateCredentialRequest(BaseModel):
    name: Optional[str] = None
    credential_pairs: Optional[Dict[Any, Any]] = None
    metadata: Optional[Dict[Any, Any]] = None
    enabled: Optional[bool] = None
    documentation: Optional[str] = None
    tags: Optional[List[str]] = None


class RestoreCredentialVersionRequest(BaseModel):
    comment: Optional[str] = None


class CredentialResponse(BaseModel):
    tenant_id: str
    id: str
    name: str
    revision: int
    enabled: bool = True
    modified_date: datetime
    modified_by: str
    documentation: Optional[str] = None
    metadata: Dict[Any, Any] = Field(default_factory=dict)
    credential_keys: List[str] = Field(default_factory=list)
    credential_pairs: Dict[Any, Any] = Field(default_factory=dict)
    permissions: Dict[str, bool] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    last_rotation_date: Optional[datetime] = None
    next_rotation_date: Optional[datetime] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_credential(
        cls,
        credential,
        include_credential_keys=False,
        include_credential_pairs=False,
    ):
        # We handle attribute access here because credential is a PynamoDB model
        # or similar object that might not be a dict.
        data = {
            'tenant_id': _value(credential, 'tenant_id'),
            'id': _value(credential, 'id'),
            'name': _value(credential, 'name'),
            'revision': _value(credential, 'revision'),
            'modified_date': _value(credential, 'modified_date'),
            'modified_by': _value(credential, 'modified_by'),
        }
        if _value(credential, 'enabled') is not None:
            data['enabled'] = _value(credential, 'enabled')
        if _value(credential, 'metadata') is not None:
            data['metadata'] = _value(credential, 'metadata')
        if _value(credential, 'documentation') is not None:
            data['documentation'] = _value(credential, 'documentation')
        if _value(credential, 'tags') is not None:
            data['tags'] = _value(credential, 'tags')
        if _value(credential, 'last_rotation_date') is not None:
            data['last_rotation_date'] = _value(credential, 'last_rotation_date')
        if _value(credential, 'next_rotation_date') is not None:
            data['next_rotation_date'] = _value(credential, 'next_rotation_date')

        if include_credential_keys:
            data['credential_keys'] = _value(credential, 'credential_keys', [])
        if include_credential_pairs:
            decrypted = _value(credential, 'decrypted_credential_pairs', None)
            if decrypted is None:
                decrypted = _value(credential, 'credential_pairs', {})
            data['credential_pairs'] = decrypted
        return cls(**data)


class CredentialsResponse(BaseModel):
    credentials: List[CredentialResponse]
    next_page: Optional[str] = None

    @classmethod
    def from_credentials(
        cls,
        credentials,
        next_page=None,
        include_credential_keys=False,
        include_credential_pairs=False,
    ):
        credentials_list = [
            CredentialResponse.from_credential(
                credential,
                include_credential_keys,
                include_credential_pairs,
            )
            for credential in credentials
        ]
        # Sort by name (case-insensitive) as per original pre_dump sort_credentials
        credentials_list.sort(key=lambda k: k.name.lower())

        return cls(
            credentials=credentials_list,
            next_page=encode_last_evaluated_key(next_page),
        )


class RevisionsResponse(BaseModel):
    versions: List[CredentialResponse]
    next_page: Optional[str] = None

    @classmethod
    def from_credentials(
        cls,
        credentials,
        next_page=None,
        include_credential_keys=False,
        include_credential_pairs=False,
    ):
        revisions_list = [
            CredentialResponse.from_credential(
                credential,
                include_credential_keys,
                include_credential_pairs,
            )
            for credential in credentials
        ]
        # Sort by revision to match historical version ordering.
        revisions_list.sort(key=lambda k: k.revision)

        return cls(
            versions=revisions_list,
            next_page=encode_last_evaluated_key(next_page),
        )


# For backward compatibility with the routes during migration,
# we provide wrappers that mimic marshmallow schema dumps.
class SchemaWrapper:
    def __init__(self, model_cls):
        self.model_cls = model_cls

    def dumps(self, obj):
        if isinstance(obj, self.model_cls):
            return obj.model_dump_json()
        return self.model_cls.model_validate(obj).model_dump_json()


credential_response_schema = SchemaWrapper(CredentialResponse)
credentials_response_schema = SchemaWrapper(CredentialsResponse)
revisions_response_schema = SchemaWrapper(RevisionsResponse)
credential_version_list_response_schema = revisions_response_schema

# For backward compatibility
CredentialResponseSchema = SchemaWrapper
CredentialsResponseSchema = SchemaWrapper
RevisionsResponseSchema = SchemaWrapper
CredentialVersionListResponseSchema = SchemaWrapper
