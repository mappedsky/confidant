from typing import List
from pydantic import BaseModel


class JWTResponse(BaseModel):
    token: str

    class Config:
        from_attributes = True


class JWKSResponse(BaseModel):
    kty: str
    kid: str
    n: str
    e: str
    alg: str

    class Config:
        from_attributes = True


class JWKSListResponse(BaseModel):
    keys: List[JWKSResponse]

    class Config:
        from_attributes = True


class SchemaWrapper:
    def __init__(self, model_cls):
        self.model_cls = model_cls

    def dumps(self, obj):
        if isinstance(obj, self.model_cls):
            return obj.model_dump_json()
        return self.model_cls.model_validate(obj).model_dump_json()


jwt_response_schema = SchemaWrapper(JWTResponse)
jwks_list_response_schema = SchemaWrapper(JWKSListResponse)

# For backward compatibility
JWTResponseSchema = SchemaWrapper
JWKSResponseSchema = SchemaWrapper
JWKSListResponseSchema = SchemaWrapper
