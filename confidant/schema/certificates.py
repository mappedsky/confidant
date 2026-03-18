from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CertificateAuthorityResponse(BaseModel):
    ca: str
    certificate: str
    certificate_chain: str
    tags: Dict[str, str] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class CertificateAuthoritiesResponse(BaseModel):
    cas: List[CertificateAuthorityResponse]

    @classmethod
    def from_cas(cls, cas):
        return cls(
            cas=[
                CertificateAuthorityResponse(
                    ca=ca['ca'],
                    certificate=ca['certificate'],
                    certificate_chain=ca['certificate_chain'],
                    tags=ca['tags'])
                for ca in cas
            ],
        )


class CertificateResponse(BaseModel):
    certificate: str
    certificate_chain: str
    key: Optional[str] = None

    class Config:
        from_attributes = True


class SchemaWrapper:
    def __init__(self, model_cls, exclude=None):
        self.model_cls = model_cls
        self.exclude = exclude

    def dumps(self, obj):
        if isinstance(obj, self.model_cls):
            return obj.model_dump_json(exclude=self.exclude)
        return self.model_cls.model_validate(obj).model_dump_json(
            exclude=self.exclude
        )


certificate_response_schema = SchemaWrapper(
    CertificateResponse,
    exclude={'key'}
)
certificate_authority_response_schema = SchemaWrapper(CertificateAuthorityResponse)
certificate_authorities_response_schema = SchemaWrapper(CertificateAuthoritiesResponse)
certificate_expanded_response_schema = SchemaWrapper(CertificateResponse)

# For backward compatibility
CertificateAuthorityResponseSchema = SchemaWrapper
CertificateAuthoritiesResponseSchema = SchemaWrapper
CertificateResponseSchema = SchemaWrapper
CertificateExpandedResponseSchema = SchemaWrapper
