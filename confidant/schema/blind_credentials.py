from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from confidant.utils.dynamodb import encode_last_evaluated_key


class BlindCredentialResponse(BaseModel):
    id: str
    name: str
    cipher_version: int
    cipher_type: str
    revision: int
    enabled: bool = True
    documentation: Optional[str] = None
    modified_date: datetime
    modified_by: str
    metadata: Dict[Any, Any] = Field(default_factory=dict)
    credential_keys: List[str] = Field(default_factory=list)
    credential_pairs: Dict[Any, Any] = Field(default_factory=dict)
    data_key: Dict[Any, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True

    @classmethod
    def from_blind_credential(
        cls,
        credential,
        include_credential_keys=False,
        include_credential_pairs=False,
        include_data_key=False,
    ):
        data = {
            'id': credential.id,
            'name': credential.name,
            'cipher_version': credential.cipher_version,
            'cipher_type': credential.cipher_type,
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

        if include_credential_keys:
            data['credential_keys'] = list(credential.credential_keys)
        if include_credential_pairs:
            data['credential_pairs'] = credential.credential_pairs
        if include_data_key:
            data['data_key'] = credential.data_key
        return cls(**data)


class SchemaWrapper:
    def __init__(self, model_cls):
        self.model_cls = model_cls

    def dumps(self, obj):
        if isinstance(obj, self.model_cls):
            return obj.model_dump_json()
        return self.model_cls.model_validate(obj).model_dump_json()


blind_credential_response_schema = SchemaWrapper(BlindCredentialResponse)
# Keeping the class names for imports during migration
BlindCredentialResponseSchema = SchemaWrapper
