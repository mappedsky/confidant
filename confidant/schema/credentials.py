from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from confidant.utils.dynamodb import encode_last_evaluated_key


class CredentialResponse(BaseModel):
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
            'id': credential.id,
            'name': credential.name,
            'revision': credential.revision,
            'modified_date': credential.modified_date,
            'modified_by': credential.modified_by,
        }
        if credential.enabled is not None:
            data['enabled'] = credential.enabled
        if credential.metadata is not None:
            data['metadata'] = credential.metadata
        if credential.documentation is not None:
            data['documentation'] = credential.documentation
        if credential.tags is not None:
            data['tags'] = credential.tags
        if credential.last_rotation_date is not None:
            data['last_rotation_date'] = credential.last_rotation_date
        if credential.next_rotation_date is not None:
            data['next_rotation_date'] = credential.next_rotation_date

        if include_credential_keys:
            data['credential_keys'] = credential.credential_keys
        if include_credential_pairs:
            data['credential_pairs'] = credential.decrypted_credential_pairs
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
    revisions: List[CredentialResponse]
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
        # Sort by revision as per original pre_dump sort_revisions
        revisions_list.sort(key=lambda k: k.revision)

        return cls(
            revisions=revisions_list,
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

# For backward compatibility
CredentialResponseSchema = SchemaWrapper
CredentialsResponseSchema = SchemaWrapper
RevisionsResponseSchema = SchemaWrapper
