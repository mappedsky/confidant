import fnmatch
import glob
import re
from typing import Any

_MAX_ID_LENGTH = 512
_SECRET_ID_PATTERN = re.compile(r"^[A-Za-z0-9/_+=.@-]{1,512}$")
_GROUP_ID_PATTERN = re.compile(r"^[A-Za-z0-9_+=.@-]{1,512}$")
_SECRET_POLICY_PATTERN = re.compile(r"^[A-Za-z0-9/_+=.@\-*?\[\]]{1,512}$")


def validate_secret_id(secret_id: Any) -> str | None:
    if not isinstance(secret_id, str):
        return "id must be a string"
    if not secret_id:
        return "id is a required field"
    if len(secret_id) > _MAX_ID_LENGTH:
        return "id must be 512 characters or fewer"
    if secret_id.endswith("/"):
        return "secret id must not end with /"
    if not _SECRET_ID_PATTERN.fullmatch(secret_id):
        msg = "secret id may only contain alphanumeric characters and /_+=.@-"
        return msg
    return None


def validate_group_id(group_id: Any) -> str | None:
    if not isinstance(group_id, str):
        return "id must be a string"
    if not group_id:
        return "id is a required field"
    if len(group_id) > _MAX_ID_LENGTH:
        return "id must be 512 characters or fewer"
    if not _GROUP_ID_PATTERN.fullmatch(group_id):
        msg = "group id may only contain alphanumeric characters and _+=.@-"
        return msg
    return None


def secret_policy_has_glob(secret_policy_path: str) -> bool:
    return glob.has_magic(secret_policy_path)


def validate_secret_policy_path(secret_policy_path: Any) -> str | None:
    if not isinstance(secret_policy_path, str):
        return "policy path must be a string"
    if not secret_policy_path:
        return "policy path is required"
    if not secret_policy_has_glob(secret_policy_path):
        return validate_secret_id(secret_policy_path)
    if len(secret_policy_path) > _MAX_ID_LENGTH:
        return "policy path must be 512 characters or fewer"
    if secret_policy_path.endswith("/"):
        return "policy path must not end with /"
    if not _SECRET_POLICY_PATTERN.fullmatch(secret_policy_path):
        msg = "policy path may only contain alphanumeric characters and"
        msg += " /_+=.@-*?[]"
        return msg
    return None


def secret_policy_matches(
    secret_policy_path: str,
    secret_id: str,
) -> bool:
    return fnmatch.fnmatchcase(secret_id, secret_policy_path)
