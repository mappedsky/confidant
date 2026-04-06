import logging

from flask import blueprints
from flask import jsonify
from flask import request

from confidant import authnz
from confidant import settings
from confidant.schema.groups import group_response_schema
from confidant.schema.groups import GroupResponse
from confidant.schema.groups import groups_response_schema
from confidant.schema.groups import revisions_response_schema
from confidant.services import groupmanager
from confidant.services import secretmanager
from confidant.utils import maintenance
from confidant.utils import misc
from confidant.utils import stats
from confidant.utils.dynamodb import decode_last_evaluated_key

logger = logging.getLogger(__name__)
blueprint = blueprints.Blueprint("groups", __name__)

acl_module_check = misc.load_module(settings.ACL_MODULE)


@blueprint.route("/v1/groups", methods=["GET"])
@misc.prevent_xss_decorator
@authnz.require_auth
def get_group_list():
    with stats.timer("list_groups"):
        if not acl_module_check(resource_type="group", action="list"):
            msg = "{} does not have access to list groups".format(
                authnz.get_logged_in_user()
            )
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
            msg = "{} does not have access to get group {}".format(
                authnz.get_logged_in_user(),
                id,
            )
            return jsonify({"error": msg, "reference": id}), 403

        group = groupmanager.get_group_latest(tenant_id, id)
        if not group:
            return jsonify({}), 404
        if authnz.user_is_user_type("user"):
            permissions["update"] = acl_module_check(
                resource_type="group",
                action="update",
                resource_id=id,
                kwargs={
                    "secret_ids": list(group.secrets),
                },
            )
            permissions["delete"] = acl_module_check(
                resource_type="group",
                action="delete",
                resource_id=id,
                kwargs={
                    "secret_ids": list(group.secrets),
                },
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
        msg = "{} does not have access to group {} versions".format(
            authnz.get_logged_in_user(),
            id,
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
        msg = "{} does not have access to group {}".format(
            authnz.get_logged_in_user(),
            id,
        )
        return jsonify({"error": msg, "reference": id}), 403
    response = groupmanager.get_group_version(tenant_id, id, version)
    if not response:
        return jsonify({}), 404
    expanded = GroupResponse.from_group(response)
    expanded.permissions = {
        "get": True,
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
@authnz.require_csrf_token
@maintenance.check_maintenance_mode
def update_group(id):
    data = request.get_json() or {}
    tenant_id = authnz.get_tenant_id()
    existing = groupmanager.get_group_latest(tenant_id, id)
    secrets = data.get("secrets", [])
    if not isinstance(secrets, list):
        return jsonify({"error": "secrets must be a list"}), 400

    found_secrets = secretmanager.get_secrets(
        tenant_id,
        secrets,
        include_secret_keys=True,
        include_secret_pairs=True,
    )
    if len(found_secrets) != len(secrets):
        return jsonify({"error": "Secret not found."}), 404

    if existing is None:
        create_allowed = acl_module_check(
            resource_type="group",
            action="create",
            resource_id=id,
        )
        if not create_allowed:
            msg = "{} does not have access to create group {}".format(
                authnz.get_logged_in_user(),
                id,
            )
            return jsonify({"error": msg, "reference": id}), 403
        response, error = groupmanager.create_group(
            tenant_id=tenant_id,
            group_id=id,
            secrets=[secret.id for secret in found_secrets],
            created_by=authnz.get_logged_in_user(),
        )
    else:
        if not acl_module_check(
            resource_type="group",
            action="update",
            resource_id=id,
        ):
            msg = "{} does not have access to update group {}".format(
                authnz.get_logged_in_user(),
                id,
            )
            return jsonify({"error": msg, "reference": id}), 403
        response, error = groupmanager.update_group(
            tenant_id=tenant_id,
            group_id=id,
            secrets=[secret.id for secret in found_secrets],
            created_by=authnz.get_logged_in_user(),
        )
    if error:
        return jsonify(error), 400
    expanded = GroupResponse.from_group(response)
    expanded.permissions = {
        "create": existing is None,
        "metadata": True,
        "get": True,
        "update": True,
        "delete": acl_module_check(
            resource_type="group",
            action="delete",
            resource_id=response.id,
        ),
    }
    return group_response_schema.dumps(expanded)


@blueprint.route(
    "/v1/groups/<id>/versions/<int:version>/restore",
    methods=["POST"],
)
@misc.prevent_xss_decorator
@authnz.require_auth
@authnz.require_csrf_token
@maintenance.check_maintenance_mode
def restore_group_version(id, version):
    tenant_id = authnz.get_tenant_id()
    if not acl_module_check(
        resource_type="group",
        action="revert",
        resource_id=id,
    ):
        msg = "{} does not have access to revert group {}".format(
            authnz.get_logged_in_user(),
            id,
        )
        return jsonify({"error": msg, "reference": id}), 403
    response = groupmanager.restore_group_version(
        tenant_id=tenant_id,
        group_id=id,
        version=version,
        created_by=authnz.get_logged_in_user(),
    )
    if not response:
        return jsonify({}), 404
    expanded = GroupResponse.from_group(response)
    expanded.permissions = {
        "metadata": True,
        "get": True,
        "update": True,
        "delete": acl_module_check(
            resource_type="group",
            action="delete",
            resource_id=id,
        ),
    }
    return group_response_schema.dumps(expanded)


@blueprint.route("/v1/groups/<id>", methods=["DELETE"])
@misc.prevent_xss_decorator
@authnz.require_auth
@authnz.require_csrf_token
@maintenance.check_maintenance_mode
def delete_group(id):
    tenant_id = authnz.get_tenant_id()
    if not acl_module_check(
        resource_type="group",
        action="delete",
        resource_id=id,
    ):
        msg = "{} does not have access to delete group {}".format(
            authnz.get_logged_in_user(),
            id,
        )
        return jsonify({"error": msg, "reference": id}), 403
    response, error = groupmanager.delete_group(
        tenant_id=tenant_id,
        group_id=id,
    )
    if error:
        return jsonify(error), 404
    expanded = GroupResponse.from_group(response)
    expanded.permissions = {
        "metadata": True,
        "get": True,
        "update": False,
        "delete": True,
    }
    return group_response_schema.dumps(expanded)
