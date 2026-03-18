from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field

from confidant.schema.blind_credentials import BlindCredentialResponse
from confidant.schema.credentials import CredentialResponse
from confidant.utils.dynamodb import encode_last_evaluated_key


class ServiceResponse(BaseModel):
    id: str
    account: Optional[str] = None
    revision: int
    enabled: bool = True
    modified_date: datetime
    modified_by: str
    credentials: List[Union[str, CredentialResponse]] = Field(default_factory=list)
    blind_credentials: List[Union[str, BlindCredentialResponse]] = Field(
        default_factory=list
    )
    permissions: Dict[str, bool] = Field(default_factory=dict)

    class Config:
        from_attributes = True

    @classmethod
    def from_service(
        cls,
        service,
        include_credentials=False,
        include_blind_credentials=False,
    ):
        data = {
            'id': service.id,
            'revision': service.revision,
            'modified_date': service.modified_date,
            'modified_by': service.modified_by,
        }
        if service.account is not None:
            data['account'] = service.account
        if service.enabled is not None:
            data['enabled'] = service.enabled

        if include_credentials:
            data['credentials'] = service.credentials
        if include_blind_credentials:
            data['blind_credentials'] = service.blind_credentials
        return cls(**data)

    @classmethod
    def from_service_expanded(
        cls,
        service,
        credentials,
        blind_credentials,
        metadata_only=True,
    ):
        data = {
            'id': service.id,
            'revision': service.revision,
            'modified_date': service.modified_date,
            'modified_by': service.modified_by,
        }
        if service.account is not None:
            data['account'] = service.account
        if service.enabled is not None:
            data['enabled'] = service.enabled

        include_sensitive = not metadata_only
        data['credentials'] = [
            CredentialResponse.from_credential(
                credential,
                include_credential_keys=True,
                include_credential_pairs=include_sensitive,
            )
            for credential in credentials
        ]
        data['blind_credentials'] = [
            BlindCredentialResponse.from_blind_credential(
                blind_credential,
                include_credential_keys=True,
                include_credential_pairs=include_sensitive,
                include_data_key=include_sensitive,
            )
            for blind_credential in blind_credentials
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
        include_blind_credentials=False,
    ):
        services_list = [
            ServiceResponse.from_service(
                service,
                include_credentials=include_credentials,
                include_blind_credentials=include_blind_credentials,
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
    revisions: List[ServiceResponse]
    next_page: Optional[str] = None

    @classmethod
    def from_services(
        cls,
        services,
        include_credentials=False,
        include_blind_credentials=False,
        next_page=None,
    ):
        revisions_list = [
            ServiceResponse.from_service(
                service,
                include_credentials=include_credentials,
                include_blind_credentials=include_blind_credentials,
            )
            for service in services
        ]
        # Sort by revision as per original pre_dump sort_revisions
        revisions_list.sort(key=lambda k: k.revision)
        return cls(
            revisions=revisions_list,
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

# For backward compatibility
ServiceResponseSchema = SchemaWrapper
ServiceExpandedResponseSchema = SchemaWrapper
ServicesResponseSchema = SchemaWrapper
RevisionsResponseSchema = SchemaWrapper
