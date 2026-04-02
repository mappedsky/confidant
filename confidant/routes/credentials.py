import logging

from flask import blueprints
from flask import jsonify
from flask import request

from confidant import authnz
from confidant import settings
from confidant.schema.credentials import (
    credential_response_schema,
    credentials_response_schema,
    revisions_response_schema,
)
from confidant.services import credentialmanager
from confidant.services import servicemanager
from confidant.utils import maintenance
from confidant.utils import misc
from confidant.utils import stats
from confidant.utils.dynamodb import decode_last_evaluated_key

logger = logging.getLogger(__name__)
blueprint = blueprints.Blueprint("credentials", __name__)

acl_module_check = misc.load_module(settings.ACL_MODULE)


def _service_has_credential_access(tenant_id, credential_id):
    if not settings.USE_AUTH or not authnz.user_is_user_type("service"):
        return False
    service = servicemanager.get_service_latest(
        tenant_id,
        authnz.get_logged_in_user(),
    )
    if not service:
        return False
    if not authnz.service_in_account(service.account):
        return False
    return credential_id in (service.credentials or [])


def _read_action_for_request():
    if settings.USE_AUTH and authnz.user_is_user_type("service"):
        return "read"
    return "read_with_alert"


def _should_alert_on_read():
    return _read_action_for_request() == "read_with_alert"


def _can_view_credential_metadata(tenant_id, credential_id):
    if _can_read_credential(tenant_id, credential_id, "metadata"):
        return True
    if _can_read_credential(tenant_id, credential_id, "read"):
        return True
    return _can_read_credential(tenant_id, credential_id, "read_with_alert")


def _can_read_credential(tenant_id, credential_id, action):
    if acl_module_check(
        resource_type="credential",
        action=action,
        resource_id=credential_id,
    ):
        return True
    return _service_has_credential_access(tenant_id, credential_id)


@blueprint.route("/v1/credentials", methods=["GET"])
@misc.prevent_xss_decorator
@authnz.require_auth
def get_credential_list():
    with stats.timer("list_credentials"):
        if not acl_module_check(resource_type="credential", action="list"):
            msg = "{} does not have access to list credentials".format(
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
        response = credentialmanager.list_credentials(
            tenant_id,
            limit=limit,
            page=page,
        )
        return credentials_response_schema.dumps(response)


@blueprint.route("/v1/credentials/<id>", methods=["GET"])
@misc.prevent_xss_decorator
@authnz.require_auth
def get_credential(id):
    with stats.timer("get_credential_by_id"):
        tenant_id = authnz.get_tenant_id()
        metadata_only = misc.get_boolean(request.args.get("metadata_only"))
        action = "metadata" if metadata_only else _read_action_for_request()
        can_access = (
            _can_view_credential_metadata(tenant_id, id)
            if metadata_only
            else _can_read_credential(tenant_id, id, action)
        )
        if not can_access:
            msg = "{} does not have access to credential {}".format(
                authnz.get_logged_in_user(),
                id,
            )
            return jsonify({"error": msg, "reference": id}), 403
        response = credentialmanager.get_credential_latest(
            tenant_id,
            id,
            metadata_only=metadata_only,
            alert_on_access=not metadata_only and _should_alert_on_read(),
        )
        if not response:
            return jsonify({}), 404
        if metadata_only:
            response.credential_pairs = {}
        response.permissions = {
            "metadata": True,
            "read": not metadata_only and not _should_alert_on_read(),
            "read_with_alert": not metadata_only and _should_alert_on_read(),
            "update": acl_module_check(
                resource_type="credential",
                action="update",
                resource_id=id,
            ),
        }
        return credential_response_schema.dumps(response)


@blueprint.route("/v1/credentials/<id>/versions", methods=["GET"])
@misc.prevent_xss_decorator
@authnz.require_auth
def list_credential_versions(id):
    tenant_id = authnz.get_tenant_id()
    if not _can_view_credential_metadata(tenant_id, id):
        msg = "{} does not have access to credential {} versions".format(
            authnz.get_logged_in_user(),
            id,
        )
        return jsonify({"error": msg}), 403
    response = credentialmanager.list_credential_versions(tenant_id, id)
    if not response.versions:
        return jsonify({}), 404
    return revisions_response_schema.dumps(response)


@blueprint.route("/v1/credentials/<id>/versions/<int:version>", methods=["GET"])
@misc.prevent_xss_decorator
@authnz.require_auth
def get_credential_version(id, version):
    tenant_id = authnz.get_tenant_id()
    read_action = _read_action_for_request()
    if not _can_read_credential(tenant_id, id, read_action):
        msg = "{} does not have access to credential {}".format(
            authnz.get_logged_in_user(),
            id,
        )
        return jsonify({"error": msg}), 403
    response = credentialmanager.get_credential_version(
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
            resource_type="credential",
            action="update",
            resource_id=id,
        ),
    }
    return credential_response_schema.dumps(response)


@blueprint.route("/v1/credentials", methods=["POST"])
@misc.prevent_xss_decorator
@authnz.require_auth
@authnz.require_csrf_token
@maintenance.check_maintenance_mode
def create_credential():
    with stats.timer("create_credential"):
        if not acl_module_check(resource_type="credential", action="create"):
            msg = f"{authnz.get_logged_in_user()} does not have access to create credentials"
            return jsonify({"error": msg}), 403
        data = request.get_json() or {}
        tenant_id = authnz.get_tenant_id()
        if not data.get("documentation") and settings.get("ENFORCE_DOCUMENTATION"):
            return jsonify({"error": "documentation is a required field"}), 400
        if not data.get("name"):
            return jsonify({"error": "name is a required field"}), 400
        if not data.get("credential_pairs"):
            return jsonify({"error": "credential_pairs is a required field"}), 400
        if not isinstance(data.get("metadata", {}), dict):
            return jsonify({"error": "metadata must be a dict"}), 400
        response, error = credentialmanager.create_credential(
            tenant_id=tenant_id,
            name=data.get("name"),
            credential_pairs=data["credential_pairs"],
            created_by=authnz.get_logged_in_user(),
            enabled=data.get("enabled", True),
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
        }
        return credential_response_schema.dumps(response)


@blueprint.route("/v1/credentials/<id>", methods=["PUT"])
@blueprint.route("/v1/credentials/<id>/versions", methods=["POST"])
@misc.prevent_xss_decorator
@authnz.require_auth
@authnz.require_csrf_token
@maintenance.check_maintenance_mode
def update_credential(id):
    with stats.timer("update_credential"):
        if not acl_module_check(
            resource_type="credential",
            action="update",
            resource_id=id,
        ):
            msg = f"{authnz.get_logged_in_user()} does not have access to update credential {id}"
            return jsonify({"error": msg, "reference": id}), 403
        data = request.get_json() or {}
        tenant_id = authnz.get_tenant_id()
        if not isinstance(data.get("metadata", {}), dict) and data.get("metadata") is not None:
            return jsonify({"error": "metadata must be a dict"}), 400
        response, error = credentialmanager.update_credential(
            tenant_id=tenant_id,
            credential_id=id,
            name=data.get("name"),
            created_by=authnz.get_logged_in_user(),
            credential_pairs=data.get("credential_pairs"),
            enabled=data.get("enabled"),
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
        }
        return credential_response_schema.dumps(response)


@blueprint.route("/v1/credentials/<id>/versions/<int:version>/restore", methods=["POST"])
@misc.prevent_xss_decorator
@authnz.require_auth
@authnz.require_csrf_token
@maintenance.check_maintenance_mode
def restore_credential_version(id, version):
    tenant_id = authnz.get_tenant_id()
    if not acl_module_check(
        resource_type="credential",
        action="update",
        resource_id=id,
    ):
        msg = f"{authnz.get_logged_in_user()} does not have access to update credential {id}"
        return jsonify({"error": msg, "reference": id}), 403
    response = credentialmanager.restore_credential_version(
        tenant_id=tenant_id,
        credential_id=id,
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
    return credential_response_schema.dumps(response)


@blueprint.route("/v1/credentials/<id>/services", methods=["GET"])
@authnz.require_auth
def get_credential_dependencies(id):
    tenant_id = authnz.get_tenant_id()
    if not _can_view_credential_metadata(tenant_id, id):
        msg = "{} does not have access to get dependencies for credential {}".format(
            authnz.get_logged_in_user(),
            id,
        )
        return jsonify({"error": msg, "reference": id}), 403
    services = credentialmanager.get_credential_dependencies(tenant_id, id)
    return jsonify({"services": services})
