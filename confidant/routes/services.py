import logging

from flask import blueprints
from flask import jsonify
from flask import request

from confidant import authnz
from confidant import settings
from confidant.schema.services import ServiceResponse
from confidant.schema.services import (
    service_response_schema,
    services_response_schema,
    revisions_response_schema,
)
from confidant.services import credentialmanager
from confidant.services import iamrolemanager
from confidant.services import servicemanager
from confidant.utils import maintenance
from confidant.utils import misc
from confidant.utils import stats
from confidant.utils.dynamodb import decode_last_evaluated_key

logger = logging.getLogger(__name__)
blueprint = blueprints.Blueprint("services", __name__)

acl_module_check = misc.load_module(settings.ACL_MODULE)


@blueprint.route("/v1/roles", methods=["GET"])
@authnz.require_auth
def get_iam_roles_list():
    if not acl_module_check(resource_type="service", action="list"):
        msg = "{} does not have access to list services".format(
            authnz.get_logged_in_user()
        )
        return jsonify({"error": msg}), 403
    roles = iamrolemanager.get_iam_roles()
    return jsonify({"roles": roles})


@blueprint.route("/v1/services", methods=["GET"])
@misc.prevent_xss_decorator
@authnz.require_auth
def get_service_list():
    with stats.timer("list_services"):
        if not acl_module_check(resource_type="service", action="list"):
            msg = "{} does not have access to list services".format(
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
        response = servicemanager.list_services(
            tenant_id,
            limit=limit,
            page=page,
        )
        return services_response_schema.dumps(response)


@blueprint.route("/v1/services/<id>", methods=["GET"])
@misc.prevent_xss_decorator
@authnz.require_auth
def get_service(id):
    with stats.timer("get_service_by_id"):
        tenant_id = authnz.get_tenant_id()
        permissions = {
            "get": acl_module_check(
                resource_type="service",
                action="get",
                resource_id=id,
            )
        }
        if not permissions["get"]:
            msg = "{} does not have access to get service {}".format(
                authnz.get_logged_in_user(),
                id,
            )
            return jsonify({"error": msg, "reference": id}), 403

        service = servicemanager.get_service_latest(tenant_id, id)
        if not service:
            return jsonify({}), 404
        if authnz.user_is_user_type("user"):
            permissions["update"] = acl_module_check(
                resource_type="service",
                action="update",
                resource_id=id,
                kwargs={
                    "credential_ids": list(service.credentials),
                },
            )

        response = ServiceResponse.from_service(service)
        response.permissions = permissions
        return service_response_schema.dumps(response)


@blueprint.route("/v1/services/<id>/versions", methods=["GET"])
@misc.prevent_xss_decorator
@authnz.require_auth
def list_service_versions(id):
    tenant_id = authnz.get_tenant_id()
    if not acl_module_check(
        resource_type="service",
        action="metadata",
        resource_id=id,
    ):
        msg = "{} does not have access to service {} versions".format(
            authnz.get_logged_in_user(),
            id,
        )
        return jsonify({"error": msg}), 403
    response = servicemanager.list_service_versions(tenant_id, id)
    if not response.versions:
        return jsonify({}), 404
    return revisions_response_schema.dumps(response)


@blueprint.route("/v1/services/<id>/versions/<int:version>", methods=["GET"])
@misc.prevent_xss_decorator
@authnz.require_auth
def get_service_version(id, version):
    tenant_id = authnz.get_tenant_id()
    if not acl_module_check(
        resource_type="service",
        action="get",
        resource_id=id,
    ):
        msg = "{} does not have access to service {}".format(
            authnz.get_logged_in_user(),
            id,
        )
        return jsonify({"error": msg, "reference": id}), 403
    response = servicemanager.get_service_version(tenant_id, id, version)
    if not response:
        return jsonify({}), 404
    expanded = ServiceResponse.from_service(response)
    expanded.permissions = {
        "get": True,
        "update": acl_module_check(
            resource_type="service",
            action="update",
            resource_id=id,
        ),
    }
    return service_response_schema.dumps(expanded)


@blueprint.route("/v1/services/<id>", methods=["PUT"])
@blueprint.route("/v1/services/<id>/versions", methods=["POST"])
@misc.prevent_xss_decorator
@authnz.require_auth
@authnz.require_csrf_token
@maintenance.check_maintenance_mode
def map_service_credentials(id):
    data = request.get_json() or {}
    tenant_id = authnz.get_tenant_id()
    existing = servicemanager.get_service_latest(tenant_id, id)
    credentials = data.get("credentials", [])
    if not isinstance(credentials, list):
        return jsonify({"error": "credentials must be a list"}), 400

    creds = credentialmanager.get_credentials(
        tenant_id,
        credentials,
        include_credential_keys=True,
        include_credential_pairs=True,
    )
    if len(creds) != len(credentials):
        return jsonify({"error": "Credential not found."}), 404

    if existing is None:
        create_allowed = acl_module_check(
            resource_type="service",
            action="create",
            resource_id=id,
        )
        if not create_allowed:
            msg = "{} does not have access to create service {}".format(
                authnz.get_logged_in_user(),
                id,
            )
            return jsonify({"error": msg, "reference": id}), 403
        response, error = servicemanager.create_service(
            tenant_id=tenant_id,
            service_id=id,
            credentials=[cred.id for cred in creds],
            created_by=authnz.get_logged_in_user(),
            enabled=data.get("enabled", True),
        )
    else:
        if not acl_module_check(
            resource_type="service",
            action="update",
            resource_id=id,
        ):
            msg = "{} does not have access to update service {}".format(
                authnz.get_logged_in_user(),
                id,
            )
            return jsonify({"error": msg, "reference": id}), 403
        response, error = servicemanager.update_service(
            tenant_id=tenant_id,
            service_id=id,
            credentials=[cred.id for cred in creds],
            created_by=authnz.get_logged_in_user(),
            enabled=data.get("enabled"),
        )
    if error:
        return jsonify(error), 400
    expanded = ServiceResponse.from_service(response)
    expanded.permissions = {
        "create": existing is None,
        "metadata": True,
        "get": True,
        "update": True,
    }
    return service_response_schema.dumps(expanded)


@blueprint.route("/v1/services/<id>/versions/<int:version>/restore", methods=["POST"])
@misc.prevent_xss_decorator
@authnz.require_auth
@authnz.require_csrf_token
@maintenance.check_maintenance_mode
def restore_service_version(id, version):
    data = request.get_json() or {}
    tenant_id = authnz.get_tenant_id()
    if not acl_module_check(
        resource_type="service",
        action="revert",
        resource_id=id,
    ):
        msg = "{} does not have access to revert service {}".format(
            authnz.get_logged_in_user(),
            id,
        )
        return jsonify({"error": msg, "reference": id}), 403
    response = servicemanager.restore_service_version(
        tenant_id=tenant_id,
        service_id=id,
        version=version,
        created_by=authnz.get_logged_in_user(),
    )
    if not response:
        return jsonify({}), 404
    expanded = ServiceResponse.from_service(response)
    expanded.permissions = {
        "metadata": True,
        "get": True,
        "update": True,
    }
    return service_response_schema.dumps(expanded)
