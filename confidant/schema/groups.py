from datetime import datetime

from pydantic import BaseModel
from pydantic import Field

from confidant.utils.dynamodb import encode_last_evaluated_key


def _value(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class CreateGroupRequest(BaseModel):
    secrets: list[str] = Field(default_factory=list)


class UpdateGroupRequest(BaseModel):
    secrets: list[str] | None = None


class RestoreGroupVersionRequest(BaseModel):
    comment: str | None = None


class GroupResponse(BaseModel):
    tenant_id: str
    id: str
    revision: int
    modified_date: datetime
    modified_by: str
    secrets: list[str] = Field(default_factory=list)
    permissions: dict[str, bool] = Field(default_factory=dict)

    class Config:
        from_attributes = True

    @classmethod
    def from_group(cls, group):
        data = {
            "tenant_id": _value(group, "tenant_id"),
            "id": _value(group, "id"),
            "revision": _value(group, "revision"),
            "modified_date": _value(group, "modified_date"),
            "modified_by": _value(group, "modified_by"),
            "secrets": _value(
                group,
                "secret_ids",
                _value(group, "secrets", []),
            ),
        }
        return cls(**data)


class GroupsResponse(BaseModel):
    groups: list[GroupResponse]
    next_page: str | None = None

    @classmethod
    def from_groups(cls, groups, next_page=None):
        groups_list = [GroupResponse.from_group(group) for group in groups]
        groups_list.sort(key=lambda item: item.id.lower())
        return cls(
            groups=groups_list,
            next_page=encode_last_evaluated_key(next_page),
        )


class RevisionsResponse(BaseModel):
    versions: list[GroupResponse]
    next_page: str | None = None

    @classmethod
    def from_groups(cls, groups, next_page=None):
        revisions_list = [GroupResponse.from_group(group) for group in groups]
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


group_response_schema = SchemaWrapper(GroupResponse)
group_expanded_response_schema = group_response_schema
groups_response_schema = SchemaWrapper(GroupsResponse)
revisions_response_schema = SchemaWrapper(RevisionsResponse)
group_version_list_response_schema = revisions_response_schema

GroupResponseSchema = SchemaWrapper
GroupExpandedResponseSchema = SchemaWrapper
GroupsResponseSchema = SchemaWrapper
RevisionsResponseSchema = SchemaWrapper
GroupVersionListResponseSchema = SchemaWrapper
