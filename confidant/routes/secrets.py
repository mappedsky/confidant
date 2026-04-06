import logging

from flask import blueprints
from flask import jsonify
from flask import request

from confidant import authnz
from confidant import settings
from confidant.schema.secrets import revisions_response_schema
from confidant.schema.secrets import secret_response_schema
from confidant.schema.secrets import secrets_response_schema
from confidant.services import groupmanager
from confidant.services import secretmanager
from confidant.utils import maintenance
from confidant.utils import misc
from confidant.utils import stats
from confidant.utils.dynamodb import decode_last_evaluated_key

logger = logging.getLogger(__name__)
blueprint = blueprints.Blueprint("secrets", __name__)

acl_module_check = misc.load_module(settings.ACL_MODULE)


def _service_has_secret_access(tenant_id, secret_id):
    if not settings.USE_AUTH or not authnz.user_is_user_type("service"):
        return False
    group = groupmanager.get_group_latest(
        tenant_id,
        authnz.get_logged_in_user(),
    )
    if not group:
        return False
    return secret_id in (group.secrets or [])


def _read_action_for_request():
    if settings.USE_AUTH and authnz.user_is_user_type("service"):
        return "read"
    return "read_with_alert"


def _should_alert_on_read():
    return _read_action_for_request() == "read_with_alert"


def _can_view_secret_metadata(tenant_id, secret_id):
    if _can_read_secret(tenant_id, secret_id, "metadata"):
        return True
    if _can_read_secret(tenant_id, secret_id, "read"):
        return True
    return _can_read_secret(tenant_id, secret_id, "read_with_alert")


def _can_read_secret(tenant_id, secret_id, action):
    if acl_module_check(
        resource_type="secret",
        action=action,
        resource_id=secret_id,
    ):
        return True
    return _service_has_secret_access(tenant_id, secret_id)


@blueprint.route("/v1/secrets", methods=["GET"])
@misc.prevent_xss_decorator
@authnz.require_auth
def get_secret_list():
    with stats.timer("list_secrets"):
        if not acl_module_check(resource_type="secret", action="list"):
            msg = "{} does not have access to list secrets".format(
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
        response = secretmanager.list_secrets(
            tenant_id,
            limit=limit,
            page=page,
        )
        return secrets_response_schema.dumps(response)


@blueprint.route("/v1/secrets/<id>", methods=["GET"])
@misc.prevent_xss_decorator
@authnz.require_auth
def get_secret(id):
    with stats.timer("get_secret_by_id"):
        tenant_id = authnz.get_tenant_id()
        metadata_only = misc.get_boolean(request.args.get("metadata_only"))
        action = "metadata" if metadata_only else _read_action_for_request()
        can_access = (
            _can_view_secret_metadata(tenant_id, id)
            if metadata_only
            else _can_read_secret(tenant_id, id, action)
        )
        if not can_access:
            msg = "{} does not have access to secret {}".format(
                authnz.get_logged_in_user(),
                id,
            )
            return jsonify({"error": msg, "reference": id}), 403
        response = secretmanager.get_secret_latest(
            tenant_id,
            id,
            metadata_only=metadata_only,
            alert_on_access=not metadata_only and _should_alert_on_read(),
        )
        if not response:
            return jsonify({}), 404
        if metadata_only:
            response.secret_pairs = {}
        response.permissions = {
            "metadata": True,
            "read": not metadata_only and not _should_alert_on_read(),
            "read_with_alert": not metadata_only and _should_alert_on_read(),
            "update": acl_module_check(
                resource_type="secret",
                action="update",
                resource_id=id,
            ),
            "delete": acl_module_check(
                resource_type="secret",
                action="delete",
                resource_id=id,
            ),
        }
        return secret_response_schema.dumps(response)


@blueprint.route("/v1/secrets/<id>/versions", methods=["GET"])
@misc.prevent_xss_decorator
@authnz.require_auth
def list_secret_versions(id):
    tenant_id = authnz.get_tenant_id()
    if not _can_view_secret_metadata(tenant_id, id):
        msg = "{} does not have access to secret {} versions".format(
            authnz.get_logged_in_user(),
            id,
        )
        return jsonify({"error": msg}), 403
    response = secretmanager.list_secret_versions(tenant_id, id)
    if not response.versions:
        return jsonify({}), 404
    return revisions_response_schema.dumps(response)


@blueprint.route("/v1/secrets/<id>/versions/<int:version>", methods=["GET"])
@misc.prevent_xss_decorator
@authnz.require_auth
def get_secret_version(id, version):
    tenant_id = authnz.get_tenant_id()
    read_action = _read_action_for_request()
    if not _can_read_secret(tenant_id, id, read_action):
        msg = "{} does not have access to secret {}".format(
            authnz.get_logged_in_user(),
            id,
        )
        return jsonify({"error": msg}), 403
    response = secretmanager.get_secret_version(
        tenant_id,
        id,
        version,
        alert_on_access=_should_alert_on_read(),
    )
    if not response:
        return jsonify({}), 404
    response.permissions = {
        "metadata": True,
        "read": not _should_alert_on_read(),
        "read_with_alert": _should_alert_on_read(),
        "update": acl_module_check(
            resource_type="secret",
            action="update",
            resource_id=id,
        ),
        "delete": acl_module_check(
            resource_type="secret",
            action="delete",
            resource_id=id,
        ),
    }
    return secret_response_schema.dumps(response)


@blueprint.route("/v1/secrets", methods=["POST"])
@misc.prevent_xss_decorator
@authnz.require_auth
@authnz.require_csrf_token
@maintenance.check_maintenance_mode
def create_secret():
    with stats.timer("create_secret"):
        if not acl_module_check(resource_type="secret", action="create"):
            msg = (
                f"{authnz.get_logged_in_user()} does not have access "
                "to create secrets"
            )
            return jsonify({"error": msg}), 403
        data = request.get_json() or {}
        tenant_id = authnz.get_tenant_id()
        enforce_documentation = settings.get("ENFORCE_DOCUMENTATION")
        if not data.get("documentation") and enforce_documentation:
            return jsonify({"error": "documentation is a required field"}), 400
        if not data.get("name"):
            return jsonify({"error": "name is a required field"}), 400
        if not data.get("secret_pairs"):
            return jsonify({"error": "secret_pairs is a required field"}), 400
        if not isinstance(data.get("metadata", {}), dict):
            return jsonify({"error": "metadata must be a dict"}), 400
        response, error = secretmanager.create_secret(
            tenant_id=tenant_id,
            name=data.get("name"),
            secret_pairs=data["secret_pairs"],
            created_by=authnz.get_logged_in_user(),
            metadata=data.get("metadata"),
            documentation=data.get("documentation"),
            tags=data.get("tags", []),
        )
        if error:
            return jsonify(error), 400
        response.permissions = {
            "metadata": True,
            "read": True,
            "read_with_alert": True,
            "update": True,
            "delete": acl_module_check(
                resource_type="secret",
                action="delete",
                resource_id=response.id,
            ),
        }
        return secret_response_schema.dumps(response)


@blueprint.route("/v1/secrets/<id>", methods=["PUT"])
@blueprint.route("/v1/secrets/<id>/versions", methods=["POST"])
@misc.prevent_xss_decorator
@authnz.require_auth
@authnz.require_csrf_token
@maintenance.check_maintenance_mode
def update_secret(id):
    with stats.timer("update_secret"):
        if not acl_module_check(
            resource_type="secret",
            action="update",
            resource_id=id,
        ):
            msg = (
                f"{authnz.get_logged_in_user()} does not have access "
                f"to update secret {id}"
            )
            return jsonify({"error": msg, "reference": id}), 403
        data = request.get_json() or {}
        tenant_id = authnz.get_tenant_id()
        if (
            not isinstance(data.get("metadata", {}), dict)
            and data.get("metadata") is not None
        ):
            return jsonify({"error": "metadata must be a dict"}), 400
        response, error = secretmanager.update_secret(
            tenant_id=tenant_id,
            secret_id=id,
            name=data.get("name"),
            created_by=authnz.get_logged_in_user(),
            secret_pairs=data.get("secret_pairs"),
            metadata=data.get("metadata"),
            documentation=data.get("documentation"),
            tags=data.get("tags"),
        )
        if error:
            return jsonify(error), 400
        response.permissions = {
            "metadata": True,
            "read": True,
            "read_with_alert": True,
            "update": True,
            "delete": acl_module_check(
                resource_type="secret",
                action="delete",
                resource_id=id,
            ),
        }
        return secret_response_schema.dumps(response)


@blueprint.route("/v1/secrets/<id>", methods=["DELETE"])
@misc.prevent_xss_decorator
@authnz.require_auth
@authnz.require_csrf_token
@maintenance.check_maintenance_mode
def delete_secret(id):
    tenant_id = authnz.get_tenant_id()
    if not acl_module_check(
        resource_type="secret",
        action="delete",
        resource_id=id,
    ):
        msg = (
            f"{authnz.get_logged_in_user()} does not have access "
            f"to delete secret {id}"
        )
        return jsonify({"error": msg, "reference": id}), 403
    response, error = secretmanager.delete_secret(
        tenant_id=tenant_id,
        secret_id=id,
    )
    if error:
        status = 409 if error.get("groups") else 404
        return jsonify(error), status
    return secret_response_schema.dumps(response)


@blueprint.route(
    "/v1/secrets/<id>/versions/<int:version>/restore",
    methods=["POST"],
)
@misc.prevent_xss_decorator
@authnz.require_auth
@authnz.require_csrf_token
@maintenance.check_maintenance_mode
def restore_secret_version(id, version):
    tenant_id = authnz.get_tenant_id()
    if not acl_module_check(
        resource_type="secret",
        action="update",
        resource_id=id,
    ):
        msg = (
            f"{authnz.get_logged_in_user()} does not have access "
            f"to update secret {id}"
        )
        return jsonify({"error": msg, "reference": id}), 403
    response = secretmanager.restore_secret_version(
        tenant_id=tenant_id,
        secret_id=id,
        version=version,
        created_by=authnz.get_logged_in_user(),
    )
    if not response:
        return jsonify({}), 404
    response.permissions = {
        "metadata": True,
        "read": True,
        "read_with_alert": True,
        "update": True,
    }
    return secret_response_schema.dumps(response)


@blueprint.route("/v1/secrets/<id>/groups", methods=["GET"])
@authnz.require_auth
def get_secret_dependencies(id):
    tenant_id = authnz.get_tenant_id()
    if not _can_view_secret_metadata(tenant_id, id):
        user = authnz.get_logged_in_user()
        msg = f"{user} does not have access to get dependencies for secret {id}"
        return jsonify({"error": msg, "reference": id}), 403
    groups = secretmanager.get_secret_dependencies(tenant_id, id)
    return jsonify({"groups": groups})
