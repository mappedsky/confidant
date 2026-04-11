from confidant import authnz
from confidant import settings
from confidant.services import groupmanager

BUILTIN_ADMIN_GROUP = "confidant-administrator"
BUILTIN_GROUP_ADMIN_GROUP = "confidant-group-administrator"
BUILTIN_AUDITOR_GROUP = "confidant-auditor"

GROUP_ADMIN_ACTIONS = {
    "list",
    "metadata",
    "get",
    "create",
    "update",
    "delete",
    "revert",
}

AUDITOR_ACTIONS = {
    "list",
    "metadata",
    "get",
}


def _has_any_group(group_ids, *group_names):
    return any(group_name in group_ids for group_name in group_names)


def default_acl(*args, **kwargs):
    """Default ACLs for confidant.

    Access is driven by JWT group membership:

    * confidant-administrator: full access
    * confidant-group-administrator: full group management access
    * confidant-auditor: list resources and read metadata
    * remaining group memberships are evaluated as secret policies
    """
    resource_type = kwargs.get("resource_type")
    action = kwargs.get("action")
    resource_id = kwargs.get("resource_id")
    if not settings.USE_AUTH:
        return True

    group_ids = authnz.get_logged_in_group_ids()
    if _has_any_group(group_ids, BUILTIN_ADMIN_GROUP):
        return True

    if resource_type == "group":
        if _has_any_group(group_ids, BUILTIN_GROUP_ADMIN_GROUP) and (
            action in GROUP_ADMIN_ACTIONS
        ):
            return True
        if _has_any_group(group_ids, BUILTIN_AUDITOR_GROUP) and (
            action in AUDITOR_ACTIONS
        ):
            return True
        return False

    if resource_type == "secret":
        if action == "list" and _has_any_group(
            group_ids,
            BUILTIN_AUDITOR_GROUP,
        ):
            return True
        if action == "metadata" and _has_any_group(
            group_ids,
            BUILTIN_AUDITOR_GROUP,
        ):
            return True
        if action in {"list", "create"} and not resource_id:
            return False
        tenant_id = authnz.get_tenant_id()
        groups = groupmanager.get_groups_by_ids(tenant_id, group_ids)
        for group in groups:
            if groupmanager.group_grants_secret_action(
                group,
                resource_id,
                action,
            ):
                return True
        return False

    return False


def no_acl(*args, **kwargs):
    """Stub function that always returns true
    This function is set by settings.py by the variable ACL_MODULE
    When you'd like to integrate a custom RBAC module, the ACL_MODULE
    should be repointed from this function to the function that will perform
    the ACL checks.
    """
    return True
