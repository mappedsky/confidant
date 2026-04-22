import logging

from flask import blueprints, jsonify, request

from confidant import authnz, settings
from confidant.schema.groups import (
    GroupResponse,
    group_response_schema,
    groups_response_schema,
    revisions_response_schema,
)
from confidant.services import groupmanager, secretmanager
from confidant.utils import maintenance, misc, resource_ids, stats
from confidant.utils.dynamodb import decode_last_evaluated_key
from confidant.utils.logging import audit_response

logger = logging.getLogger(__name__)
blueprint = blueprints.Blueprint("groups", __name__)

acl_module_check = misc.load_module(settings.ACL_MODULE)
_ALLOWED_POLICY_ACTIONS = {
    "list",
    "create",
    "metadata",
    "decrypt",
    "update",
    "delete",
    "revert",
}


def _normalize_group_policies(data):
    policies = data.get("policies", {})
    if not isinstance(policies, dict):
        return None, {"error": "policies must be a dict"}
    normalized = {}
    for secret_id, actions in policies.items():
        id_error = resource_ids.validate_secret_policy_path(secret_id)
        if id_error:
            return None, {"error": id_error}
        if not isinstance(actions, list):
            return None, {
                "error": "policy permissions must be lists of strings",
            }
        normalized_actions = []
        seen = set()
        for action in actions:
            if not isinstance(action, str):
                return None, {
                    "error": "policy permissions must be lists of strings",
                }
            action = action.strip().lower()
            if action not in _ALLOWED_POLICY_ACTIONS:
                return None, {"error": f"Unknown policy permission {action}"}
            if action in seen:
                continue
            seen.add(action)
            normalized_actions.append(action)
        if not normalized_actions:
            return None, {
                "error": (
                    f"policy for secret {secret_id} must include at least "
                    "one permission"
                )
            }
        normalized[secret_id] = normalized_actions
    return normalized, None


@blueprint.route("/v1/groups", methods=["GET"])
@misc.prevent_xss_decorator
@authnz.require_auth
def get_group_list():
    with stats.timer("list_groups"):
        if not acl_module_check(resource_type="group", action="list"):
            msg = f"{authnz.get_logged_in_user()} does not have access to list groups"
            return jsonify({"error": msg}), 403
        tenant_id = authnz.get_tenant_id()
        limit = request.args.get("limit", default=None, type=int)
        page = request.args.get("page", default=None, type=str)
        if page:
            try:
                page = decode_last_evaluated_key(page)
            except Exception:
                logger.exception("Failed to parse provided page")
                return jsonify({"error": "Failed to parse page"}), 400
        response = groupmanager.list_groups(
            tenant_id,
            limit=limit,
            page=page,
        )
        return groups_response_schema.dumps(response)


@blueprint.route("/v1/groups/<id>", methods=["GET"])
@misc.prevent_xss_decorator
@authnz.require_auth
def get_group(id):
    with stats.timer("get_group_by_id"):
        tenant_id = authnz.get_tenant_id()
        permissions = {
            "get": acl_module_check(
                resource_type="group",
                action="get",
                resource_id=id,
            )
        }
        if not permissions["get"]:
            msg = (
                f"{authnz.get_logged_in_user()} does not have access to get group {id}"
            )
            return jsonify({"error": msg, "reference": id}), 403

        group = groupmanager.get_group_latest(tenant_id, id)
        if not group:
            return jsonify({}), 404
        permissions["revert"] = acl_module_check(
            resource_type="group",
            action="revert",
            resource_id=id,
        )
        permissions["update"] = acl_module_check(
            resource_type="group",
            action="update",
            resource_id=id,
        )
        permissions["delete"] = acl_module_check(
            resource_type="group",
            action="delete",
            resource_id=id,
        )

        response = GroupResponse.from_group(group)
        response.permissions = permissions
        return group_response_schema.dumps(response)


@blueprint.route("/v1/groups/<id>/versions", methods=["GET"])
@misc.prevent_xss_decorator
@authnz.require_auth
def list_group_versions(id):
    tenant_id = authnz.get_tenant_id()
    if not acl_module_check(
        resource_type="group",
        action="metadata",
        resource_id=id,
    ):
        msg = (
            f"{authnz.get_logged_in_user()} does not have access to group {id} versions"
        )
        return jsonify({"error": msg}), 403
    response = groupmanager.list_group_versions(tenant_id, id)
    if not response.versions:
        return jsonify({}), 404
    return revisions_response_schema.dumps(response)


@blueprint.route("/v1/groups/<id>/versions/<int:version>", methods=["GET"])
@misc.prevent_xss_decorator
@authnz.require_auth
def get_group_version(id, version):
    tenant_id = authnz.get_tenant_id()
    if not acl_module_check(
        resource_type="group",
        action="get",
        resource_id=id,
    ):
        msg = f"{authnz.get_logged_in_user()} does not have access to group {id}"
        return jsonify({"error": msg, "reference": id}), 403
    response = groupmanager.get_group_version(tenant_id, id, version)
    if not response:
        return jsonify({}), 404
    expanded = GroupResponse.from_group(response)
    expanded.permissions = {
        "get": True,
        "revert": acl_module_check(
            resource_type="group",
            action="revert",
            resource_id=id,
        ),
        "update": acl_module_check(
            resource_type="group",
            action="update",
            resource_id=id,
        ),
        "delete": acl_module_check(
            resource_type="group",
            action="delete",
            resource_id=id,
        ),
    }
    return group_response_schema.dumps(expanded)


@blueprint.route("/v1/groups/<id>", methods=["PUT"])
@blueprint.route("/v1/groups/<id>/versions", methods=["POST"])
@misc.prevent_xss_decorator
@authnz.require_auth
@maintenance.check_maintenance_mode
def update_group(id):
    data = request.get_json() or {}
    tenant_id = authnz.get_tenant_id()
    id_error = resource_ids.validate_group_id(id)
    if id_error:
        return audit_response(
            (jsonify({"error": id_error}), 400),
            "create_or_update",
            "group",
            resource_id=id,
            outcome="invalid",
            reason="invalid_id",
        )
    body_id = data.get("id")
    if body_id is not None and body_id != id:
        return audit_response(
            (jsonify({"error": "body id must match the request path"}), 400),
            "create_or_update",
            "group",
            resource_id=id,
            outcome="invalid",
            reason="body_id_mismatch",
        )
    existing = groupmanager.get_group_latest(tenant_id, id)
    policies, error = _normalize_group_policies(data)
    if error:
        return audit_response(
            (jsonify(error), 400),
            "create_or_update",
            "group",
            resource_id=id,
            outcome="invalid",
            reason=error.get("error"),
        )
    exact_secret_ids = [
        policy_path
        for policy_path in policies
        if not resource_ids.secret_policy_has_glob(policy_path)
    ]

    found_secrets = secretmanager.get_secrets(
        tenant_id,
        exact_secret_ids,
        include_secret_keys=True,
        include_secret_pairs=True,
    )
    if len(found_secrets) != len(exact_secret_ids):
        return audit_response(
            (jsonify({"error": "Secret not found."}), 404),
            "create_or_update",
            "group",
            resource_id=id,
            outcome="not_found",
            reason="secret_not_found",
        )

    if existing is None:
        create_allowed = acl_module_check(
            resource_type="group",
            action="create",
            resource_id=id,
        )
        if not create_allowed:
            msg = f"{authnz.get_logged_in_user()} does not have access to create group {id}"
            return audit_response(
                (jsonify({"error": msg, "reference": id}), 403),
                "create",
                "group",
                resource_id=id,
                outcome="denied",
            )
        response, error = groupmanager.create_group(
            tenant_id=tenant_id,
            group_id=id,
            policies=policies,
            created_by=authnz.get_logged_in_user(),
        )
    else:
        if not acl_module_check(
            resource_type="group",
            action="update",
            resource_id=id,
        ):
            msg = f"{authnz.get_logged_in_user()} does not have access to update group {id}"
            return audit_response(
                (jsonify({"error": msg, "reference": id}), 403),
                "update",
                "group",
                resource_id=id,
                outcome="denied",
            )
        response, error = groupmanager.update_group(
            tenant_id=tenant_id,
            group_id=id,
            policies=policies,
            created_by=authnz.get_logged_in_user(),
        )
    if error:
        return audit_response(
            (jsonify(error), 400),
            "create" if existing is None else "update",
            "group",
            resource_id=id,
            outcome="invalid",
            reason=error.get("error"),
        )
    expanded = GroupResponse.from_group(response)
    expanded.permissions = {
        "create": existing is None,
        "metadata": True,
        "get": True,
        "revert": acl_module_check(
            resource_type="group",
            action="revert",
            resource_id=response.id,
        ),
        "update": acl_module_check(
            resource_type="group",
            action="update",
            resource_id=response.id,
        ),
        "delete": acl_module_check(
            resource_type="group",
            action="delete",
            resource_id=response.id,
        ),
    }
    return audit_response(
        group_response_schema.dumps(expanded),
        "create" if existing is None else "update",
        "group",
        resource_id=response.id,
        outcome="success",
        revision=response.revision,
        policy_count=len(response.policies),
    )


@blueprint.route(
    "/v1/groups/<id>/versions/<int:version>/restore",
    methods=["POST"],
)
@misc.prevent_xss_decorator
@authnz.require_auth
@maintenance.check_maintenance_mode
def restore_group_version(id, version):
    tenant_id = authnz.get_tenant_id()
    if not acl_module_check(
        resource_type="group",
        action="revert",
        resource_id=id,
    ):
        msg = f"{authnz.get_logged_in_user()} does not have access to revert group {id}"
        return audit_response(
            (jsonify({"error": msg, "reference": id}), 403),
            "restore",
            "group",
            resource_id=id,
            outcome="denied",
            version=version,
        )
    response = groupmanager.restore_group_version(
        tenant_id=tenant_id,
        group_id=id,
        version=version,
        created_by=authnz.get_logged_in_user(),
    )
    if not response:
        return audit_response(
            (jsonify({}), 404),
            "restore",
            "group",
            resource_id=id,
            outcome="not_found",
            version=version,
        )
    expanded = GroupResponse.from_group(response)
    expanded.permissions = {
        "metadata": True,
        "get": True,
        "revert": acl_module_check(
            resource_type="group",
            action="revert",
            resource_id=id,
        ),
        "update": acl_module_check(
            resource_type="group",
            action="update",
            resource_id=id,
        ),
        "delete": acl_module_check(
            resource_type="group",
            action="delete",
            resource_id=id,
        ),
    }
    return audit_response(
        group_response_schema.dumps(expanded),
        "restore",
        "group",
        resource_id=id,
        outcome="success",
        version=version,
        revision=response.revision,
        policy_count=len(response.policies),
    )


@blueprint.route("/v1/groups/<id>", methods=["DELETE"])
@misc.prevent_xss_decorator
@authnz.require_auth
@maintenance.check_maintenance_mode
def delete_group(id):
    tenant_id = authnz.get_tenant_id()
    if not acl_module_check(
        resource_type="group",
        action="delete",
        resource_id=id,
    ):
        msg = f"{authnz.get_logged_in_user()} does not have access to delete group {id}"
        return audit_response(
            (jsonify({"error": msg, "reference": id}), 403),
            "delete",
            "group",
            resource_id=id,
            outcome="denied",
        )
    response, error = groupmanager.delete_group(
        tenant_id=tenant_id,
        group_id=id,
    )
    if error:
        return audit_response(
            (jsonify(error), 404),
            "delete",
            "group",
            resource_id=id,
            outcome="not_found",
            reason=error.get("error"),
        )
    expanded = GroupResponse.from_group(response)
    expanded.permissions = {
        "metadata": True,
        "get": True,
        "revert": False,
        "update": False,
        "delete": acl_module_check(
            resource_type="group",
            action="delete",
            resource_id=id,
        ),
    }
    return audit_response(
        group_response_schema.dumps(expanded),
        "delete",
        "group",
        resource_id=id,
        outcome="success",
        revision=response.revision,
    )
