from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field

from confidant.schema.credentials import CredentialResponse
from confidant.utils.dynamodb import encode_last_evaluated_key


def _value(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class CreateServiceRequest(BaseModel):
    credentials: List[str] = Field(default_factory=list)
    enabled: bool = True
    account: Optional[str] = None


class UpdateServiceRequest(BaseModel):
    credentials: Optional[List[str]] = None
    enabled: Optional[bool] = None
    account: Optional[str] = None


class RestoreServiceVersionRequest(BaseModel):
    comment: Optional[str] = None


class ServiceResponse(BaseModel):
    tenant_id: str
    id: str
    account: Optional[str] = None
    revision: int
    enabled: bool = True
    modified_date: datetime
    modified_by: str
    credentials: List[Union[str, CredentialResponse]] = Field(default_factory=list)
    permissions: Dict[str, bool] = Field(default_factory=dict)

    class Config:
        from_attributes = True

    @classmethod
    def from_service(
        cls,
        service,
        include_credentials=False,
    ):
        data = {
            'tenant_id': _value(service, 'tenant_id'),
            'id': _value(service, 'id'),
            'revision': _value(service, 'revision'),
            'modified_date': _value(service, 'modified_date'),
            'modified_by': _value(service, 'modified_by'),
        }
        if _value(service, 'account') is not None:
            data['account'] = _value(service, 'account')
        if _value(service, 'enabled') is not None:
            data['enabled'] = _value(service, 'enabled')

        if include_credentials:
            data['credentials'] = _value(service, 'credentials', [])
        return cls(**data)

    @classmethod
    def from_service_expanded(
        cls,
        service,
        credentials,
        metadata_only=True,
    ):
        data = {
            'tenant_id': _value(service, 'tenant_id'),
            'id': _value(service, 'id'),
            'revision': _value(service, 'revision'),
            'modified_date': _value(service, 'modified_date'),
            'modified_by': _value(service, 'modified_by'),
        }
        if _value(service, 'account') is not None:
            data['account'] = _value(service, 'account')
        if _value(service, 'enabled') is not None:
            data['enabled'] = _value(service, 'enabled')

        include_sensitive = not metadata_only
        data['credentials'] = [
            CredentialResponse.from_credential(
                credential,
                include_credential_keys=True,
                include_credential_pairs=include_sensitive,
            )
            for credential in credentials
        ]
        return cls(**data)


class ServicesResponse(BaseModel):
    services: List[ServiceResponse]
    next_page: Optional[str] = None

    @classmethod
    def from_services(
        cls,
        services,
        next_page=None,
        include_credentials=False,
    ):
        services_list = [
            ServiceResponse.from_service(
                service,
                include_credentials=include_credentials,
            )
            for service in services
        ]
        # Sort by id (case-insensitive) as per original pre_dump sort_services
        services_list.sort(key=lambda k: k.id.lower())
        return cls(
            services=services_list,
            next_page=encode_last_evaluated_key(next_page),
        )


class RevisionsResponse(BaseModel):
    versions: List[ServiceResponse]
    next_page: Optional[str] = None

    @classmethod
    def from_services(
        cls,
        services,
        include_credentials=False,
        next_page=None,
    ):
        revisions_list = [
            ServiceResponse.from_service(
                service,
                include_credentials=include_credentials,
            )
            for service in services
        ]
        # Sort by revision to match historical version ordering.
        revisions_list.sort(key=lambda k: k.revision)
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


service_expanded_response_schema = SchemaWrapper(ServiceResponse)
services_response_schema = SchemaWrapper(ServicesResponse)
revisions_response_schema = SchemaWrapper(RevisionsResponse)
service_version_list_response_schema = revisions_response_schema

# For backward compatibility
ServiceResponseSchema = SchemaWrapper
ServiceExpandedResponseSchema = SchemaWrapper
ServicesResponseSchema = SchemaWrapper
RevisionsResponseSchema = SchemaWrapper
ServiceVersionListResponseSchema = SchemaWrapper
