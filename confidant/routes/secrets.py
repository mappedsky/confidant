import logging
import secrets as stdlib_secrets
import string

from flask import blueprints, jsonify, request

from confidant import authnz, settings
from confidant.schema.secrets import (
    revisions_response_schema,
    secret_response_schema,
    secrets_response_schema,
)
from confidant.services import secretmanager
from confidant.utils import maintenance, misc, resource_ids, stats
from confidant.utils.dynamodb import decode_last_evaluated_key
from confidant.utils.logging import audit_response

logger = logging.getLogger(__name__)
blueprint = blueprints.Blueprint("secrets", __name__)

acl_module_check = misc.load_module(settings.ACL_MODULE)
_VALUE_GENERATOR_MIN_LENGTH = 1
_VALUE_GENERATOR_MAX_LENGTH = 1024
_VALUE_GENERATOR_CHARSETS = {
    "lowercase": string.ascii_lowercase,
    "uppercase": string.ascii_uppercase,
    "digits": string.digits,
    "symbols": string.punctuation,
}


def _can_view_secret_metadata(tenant_id, secret_id):
    if acl_module_check(
        resource_type="secret",
        action="metadata",
        resource_id=secret_id,
    ):
        return True
    return _can_decrypt_secret(tenant_id, secret_id)


def _can_decrypt_secret(tenant_id, secret_id):
    return acl_module_check(
        resource_type="secret",
        action="decrypt",
        resource_id=secret_id,
    )


def _can_list_secret(tenant_id, secret_id):
    return acl_module_check(
        resource_type="secret",
        action="list",
        resource_id=secret_id,
    )


def _can_create_secret(tenant_id, secret_id):
    return acl_module_check(
        resource_type="secret",
        action="create",
        resource_id=secret_id,
    )


def _can_revert_secret(tenant_id, secret_id):
    return acl_module_check(
        resource_type="secret",
        action="revert",
        resource_id=secret_id,
    )


def _can_update_secret(tenant_id, secret_id):
    return acl_module_check(
        resource_type="secret",
        action="update",
        resource_id=secret_id,
    )


def _can_delete_secret(tenant_id, secret_id):
    return acl_module_check(
        resource_type="secret",
        action="delete",
        resource_id=secret_id,
    )


def _secret_permissions(tenant_id, secret_id):
    return {
        "metadata": True,
        "decrypt": _can_decrypt_secret(tenant_id, secret_id),
        "revert": _can_revert_secret(tenant_id, secret_id),
        "update": _can_update_secret(tenant_id, secret_id),
        "delete": _can_delete_secret(tenant_id, secret_id),
    }


def _parse_value_generator_complexity(args):
    raw_values = args.getlist("complexity")
    if not raw_values:
        return list(_VALUE_GENERATOR_CHARSETS)

    values = []
    for raw_value in raw_values:
        if raw_value is None:
            continue
        for item in str(raw_value).split(","):
            item = item.strip().lower()
            if not item:
                continue
            if item not in _VALUE_GENERATOR_CHARSETS:
                return None
            if item not in values:
                values.append(item)
    return values or None


def _build_generated_value(length, complexity):
    charsets = [_VALUE_GENERATOR_CHARSETS[item] for item in complexity]
    if length < len(charsets):
        return None

    chars = [stdlib_secrets.choice(charset) for charset in charsets]
    all_chars = "".join(charsets)
    remaining = length - len(chars)
    chars.extend(stdlib_secrets.choice(all_chars) for _ in range(remaining))
    stdlib_secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


@blueprint.route("/v1/secrets", methods=["GET"])
@misc.prevent_xss_decorator
@authnz.require_auth
def get_secret_list():
    with stats.timer("list_secrets"):
        tenant_id = authnz.get_tenant_id()
        limit = request.args.get("limit", default=None, type=int)
        page = request.args.get("page", default=None, type=str)
        prefix = request.args.get("prefix", default=None, type=str)
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
            prefix=prefix,
        )
        response = response.model_copy(
            update={
                "secrets": [
                    secret
                    for secret in response.secrets
                    if _can_list_secret(tenant_id, secret.id)
                ]
            }
        )
        return secrets_response_schema.dumps(response)


@blueprint.route("/v1/secrets/<path:id>", methods=["GET"])
@misc.prevent_xss_decorator
@authnz.require_auth
def get_secret(id):
    with stats.timer("get_secret_by_id"):
        tenant_id = authnz.get_tenant_id()
        if not _can_view_secret_metadata(tenant_id, id):
            msg = f"{authnz.get_logged_in_user()} does not have access to secret {id}"
            return jsonify({"error": msg, "reference": id}), 403
        response = secretmanager.get_secret_latest(
            tenant_id,
            id,
            metadata_only=True,
            alert_on_access=False,
        )
        if not response:
            return jsonify({}), 404
        response.secret_pairs = {}
        response.permissions = _secret_permissions(tenant_id, id)
        return secret_response_schema.dumps(response)


@blueprint.route("/v1/secrets/<path:id>/decrypt", methods=["POST"])
@misc.prevent_xss_decorator
@authnz.require_auth
def decrypt_secret(id):
    tenant_id = authnz.get_tenant_id()
    if not _can_decrypt_secret(tenant_id, id):
        msg = (
            f"{authnz.get_logged_in_user()} does not have access to decrypt secret {id}"
        )
        return audit_response(
            (jsonify({"error": msg, "reference": id}), 403),
            "decrypt",
            "secret",
            resource_id=id,
            outcome="denied",
        )
    response = secretmanager.get_secret_latest(
        tenant_id,
        id,
        metadata_only=False,
        alert_on_access=True,
    )
    if not response:
        return audit_response(
            (jsonify({}), 404),
            "decrypt",
            "secret",
            resource_id=id,
            outcome="not_found",
        )
    response.permissions = _secret_permissions(tenant_id, id)
    return audit_response(
        secret_response_schema.dumps(response),
        "decrypt",
        "secret",
        resource_id=id,
        outcome="success",
        revision=response.revision,
        secret_key_count=len(response.secret_keys),
    )


@blueprint.route("/v1/secrets/<path:id>/versions", methods=["GET"])
@misc.prevent_xss_decorator
@authnz.require_auth
def list_secret_versions(id):
    tenant_id = authnz.get_tenant_id()
    if not _can_view_secret_metadata(tenant_id, id):
        msg = f"{authnz.get_logged_in_user()} does not have access to secret {id} versions"
        return jsonify({"error": msg}), 403
    response = secretmanager.list_secret_versions(tenant_id, id)
    if not response.versions:
        return jsonify({}), 404
    return revisions_response_schema.dumps(response)


@blueprint.route(
    "/v1/secrets/<path:id>/versions/<int:version>",
    methods=["GET"],
)
@misc.prevent_xss_decorator
@authnz.require_auth
def get_secret_version(id, version):
    tenant_id = authnz.get_tenant_id()
    if not _can_view_secret_metadata(tenant_id, id):
        msg = f"{authnz.get_logged_in_user()} does not have access to secret {id}"
        return jsonify({"error": msg}), 403
    response = secretmanager.get_secret_version(
        tenant_id,
        id,
        version,
        metadata_only=True,
    )
    if not response:
        return jsonify({}), 404
    response.permissions = _secret_permissions(tenant_id, id)
    return secret_response_schema.dumps(response)


@blueprint.route(
    "/v1/secrets/<path:id>/versions/<int:version>/decrypt",
    methods=["POST"],
)
@misc.prevent_xss_decorator
@authnz.require_auth
def decrypt_secret_version(id, version):
    tenant_id = authnz.get_tenant_id()
    if not _can_decrypt_secret(tenant_id, id):
        msg = (
            f"{authnz.get_logged_in_user()} does not have access "
            f"to decrypt secret {id} version {version}"
        )
        return audit_response(
            (jsonify({"error": msg, "reference": id}), 403),
            "decrypt_version",
            "secret",
            resource_id=id,
            outcome="denied",
            version=version,
        )
    response = secretmanager.get_secret_version(
        tenant_id,
        id,
        version,
        metadata_only=False,
        alert_on_access=True,
    )
    if not response:
        return audit_response(
            (jsonify({}), 404),
            "decrypt_version",
            "secret",
            resource_id=id,
            outcome="not_found",
            version=version,
        )
    response.permissions = _secret_permissions(tenant_id, id)
    return audit_response(
        secret_response_schema.dumps(response),
        "decrypt_version",
        "secret",
        resource_id=id,
        outcome="success",
        version=version,
        revision=response.revision,
        secret_key_count=len(response.secret_keys),
    )


@blueprint.route("/v1/secrets", methods=["POST"])
@misc.prevent_xss_decorator
@authnz.require_auth
@maintenance.check_maintenance_mode
def create_secret():
    with stats.timer("create_secret"):
        data = request.get_json() or {}
        tenant_id = authnz.get_tenant_id()
        enforce_documentation = settings.get("ENFORCE_DOCUMENTATION")
        if not data.get("documentation") and enforce_documentation:
            return audit_response(
                (jsonify({"error": "documentation is a required field"}), 400),
                "create",
                "secret",
                resource_id=data.get("id"),
                outcome="invalid",
                reason="missing_documentation",
            )
        if not data.get("id"):
            return audit_response(
                (jsonify({"error": "id is a required field"}), 400),
                "create",
                "secret",
                outcome="invalid",
                reason="missing_id",
            )
        id_error = resource_ids.validate_secret_id(data.get("id"))
        if id_error:
            return audit_response(
                (jsonify({"error": id_error}), 400),
                "create",
                "secret",
                resource_id=data.get("id"),
                outcome="invalid",
                reason="invalid_id",
            )
        if not _can_create_secret(tenant_id, data.get("id")):
            msg = (
                f"{authnz.get_logged_in_user()} does not have access "
                f"to create secret {data.get('id')}"
            )
            return audit_response(
                (jsonify({"error": msg, "reference": data.get("id")}), 403),
                "create",
                "secret",
                resource_id=data.get("id"),
                outcome="denied",
            )
        if not data.get("name"):
            return audit_response(
                (jsonify({"error": "name is a required field"}), 400),
                "create",
                "secret",
                resource_id=data.get("id"),
                outcome="invalid",
                reason="missing_name",
            )
        if not data.get("secret_pairs"):
            return audit_response(
                (jsonify({"error": "secret_pairs is a required field"}), 400),
                "create",
                "secret",
                resource_id=data.get("id"),
                outcome="invalid",
                reason="missing_secret_pairs",
            )
        if not isinstance(data.get("metadata", {}), dict):
            return audit_response(
                (jsonify({"error": "metadata must be a dict"}), 400),
                "create",
                "secret",
                resource_id=data.get("id"),
                outcome="invalid",
                reason="invalid_metadata",
            )
        response, error = secretmanager.create_secret(
            tenant_id=tenant_id,
            secret_id=data.get("id"),
            name=data.get("name"),
            secret_pairs=data["secret_pairs"],
            created_by=authnz.get_logged_in_user(),
            metadata=data.get("metadata"),
            documentation=data.get("documentation"),
        )
        if error:
            return audit_response(
                (jsonify(error), 400),
                "create",
                "secret",
                resource_id=data.get("id"),
                outcome="invalid",
                reason=error.get("error"),
            )
        response.permissions = {
            "metadata": True,
            "decrypt": _can_decrypt_secret(tenant_id, response.id),
            "revert": _can_revert_secret(tenant_id, response.id),
            "update": _can_update_secret(tenant_id, response.id),
            "delete": _can_delete_secret(tenant_id, response.id),
        }
        return audit_response(
            secret_response_schema.dumps(response),
            "create",
            "secret",
            resource_id=response.id,
            outcome="success",
            revision=response.revision,
            secret_key_count=len(response.secret_keys),
        )


@blueprint.route("/v1/secrets/<path:id>", methods=["PUT"])
@blueprint.route("/v1/secrets/<path:id>/versions", methods=["POST"])
@misc.prevent_xss_decorator
@authnz.require_auth
@maintenance.check_maintenance_mode
def update_secret(id):
    with stats.timer("update_secret"):
        tenant_id = authnz.get_tenant_id()
        if not _can_update_secret(tenant_id, id):
            msg = (
                f"{authnz.get_logged_in_user()} does not have access "
                f"to update secret {id}"
            )
            return audit_response(
                (jsonify({"error": msg, "reference": id}), 403),
                "update",
                "secret",
                resource_id=id,
                outcome="denied",
            )
        data = request.get_json() or {}
        if (
            not isinstance(data.get("metadata", {}), dict)
            and data.get("metadata") is not None
        ):
            return audit_response(
                (jsonify({"error": "metadata must be a dict"}), 400),
                "update",
                "secret",
                resource_id=id,
                outcome="invalid",
                reason="invalid_metadata",
            )
        response, error = secretmanager.update_secret(
            tenant_id=tenant_id,
            secret_id=id,
            name=data.get("name"),
            created_by=authnz.get_logged_in_user(),
            secret_pairs=data.get("secret_pairs"),
            metadata=data.get("metadata"),
            documentation=data.get("documentation"),
        )
        if error:
            return audit_response(
                (jsonify(error), 400),
                "update",
                "secret",
                resource_id=id,
                outcome="invalid",
                reason=error.get("error"),
            )
        response.permissions = {
            "metadata": True,
            "decrypt": _can_decrypt_secret(tenant_id, id),
            "revert": _can_revert_secret(tenant_id, id),
            "update": _can_update_secret(tenant_id, id),
            "delete": _can_delete_secret(tenant_id, id),
        }
        return audit_response(
            secret_response_schema.dumps(response),
            "update",
            "secret",
            resource_id=id,
            outcome="success",
            revision=response.revision,
            secret_key_count=len(response.secret_keys),
        )


@blueprint.route("/v1/secrets/<path:id>", methods=["DELETE"])
@misc.prevent_xss_decorator
@authnz.require_auth
@maintenance.check_maintenance_mode
def delete_secret(id):
    tenant_id = authnz.get_tenant_id()
    if not _can_delete_secret(tenant_id, id):
        msg = (
            f"{authnz.get_logged_in_user()} does not have access to delete secret {id}"
        )
        return audit_response(
            (jsonify({"error": msg, "reference": id}), 403),
            "delete",
            "secret",
            resource_id=id,
            outcome="denied",
        )
    response, error = secretmanager.delete_secret(
        tenant_id=tenant_id,
        secret_id=id,
    )
    if error:
        status = 409 if error.get("groups") else 404
        return audit_response(
            (jsonify(error), status),
            "delete",
            "secret",
            resource_id=id,
            outcome="conflict" if status == 409 else "not_found",
            groups=error.get("groups"),
            reason=error.get("error"),
        )
    return audit_response(
        secret_response_schema.dumps(response),
        "delete",
        "secret",
        resource_id=id,
        outcome="success",
        revision=response.revision,
    )


@blueprint.route(
    "/v1/secrets/<path:id>/versions/<int:version>/restore",
    methods=["POST"],
)
@misc.prevent_xss_decorator
@authnz.require_auth
@maintenance.check_maintenance_mode
def restore_secret_version(id, version):
    tenant_id = authnz.get_tenant_id()
    if not _can_revert_secret(tenant_id, id):
        msg = (
            f"{authnz.get_logged_in_user()} does not have access to restore secret {id}"
        )
        return audit_response(
            (jsonify({"error": msg, "reference": id}), 403),
            "restore",
            "secret",
            resource_id=id,
            outcome="denied",
            version=version,
        )
    response = secretmanager.restore_secret_version(
        tenant_id=tenant_id,
        secret_id=id,
        version=version,
        created_by=authnz.get_logged_in_user(),
    )
    if not response:
        return audit_response(
            (jsonify({}), 404),
            "restore",
            "secret",
            resource_id=id,
            outcome="not_found",
            version=version,
        )
    response.permissions = {
        "metadata": True,
        "decrypt": _can_decrypt_secret(tenant_id, id),
        "revert": _can_revert_secret(tenant_id, id),
        "update": _can_update_secret(tenant_id, id),
        "delete": _can_delete_secret(tenant_id, id),
    }
    return audit_response(
        secret_response_schema.dumps(response),
        "restore",
        "secret",
        resource_id=id,
        outcome="success",
        version=version,
        revision=response.revision,
    )


@blueprint.route("/v1/secrets/<path:id>/groups", methods=["GET"])
@authnz.require_auth
def get_secret_dependencies(id):
    tenant_id = authnz.get_tenant_id()
    if not _can_view_secret_metadata(tenant_id, id):
        user = authnz.get_logged_in_user()
        msg = f"{user} does not have access to get dependencies for secret {id}"
        return jsonify({"error": msg, "reference": id}), 403
    groups = secretmanager.get_secret_dependencies(tenant_id, id)
    return jsonify({"groups": groups})


@blueprint.route("/v1/value_generator", methods=["GET"])
@misc.prevent_xss_decorator
@authnz.require_auth
def generate_value():
    raw_length = request.args.get("length")
    if raw_length is None:
        length = 32
    else:
        try:
            length = int(raw_length)
        except (TypeError, ValueError):
            return jsonify({"error": "length must be an integer"}), 400

    if length is None:
        return jsonify({"error": "length must be an integer"}), 400
    too_short = length < _VALUE_GENERATOR_MIN_LENGTH
    too_long = length > _VALUE_GENERATOR_MAX_LENGTH
    if too_short or too_long:
        return (
            jsonify(
                {
                    "error": (
                        f"length must be between {_VALUE_GENERATOR_MIN_LENGTH} "
                        f"and {_VALUE_GENERATOR_MAX_LENGTH}"
                    )
                }
            ),
            400,
        )

    complexity = _parse_value_generator_complexity(request.args)
    if complexity is None:
        return (
            jsonify(
                {
                    "error": (
                        "complexity must be one or more of "
                        "lowercase, uppercase, digits, symbols"
                    )
                }
            ),
            400,
        )

    value = _build_generated_value(length, complexity)
    if value is None:
        error = "length must be at least the number of selected classes"
        return jsonify({"error": error}), 400

    return jsonify({"value": value})
