from urllib.parse import urlparse

from flask import blueprints
from flask import jsonify

from confidant import authnz
from confidant import settings
from confidant.utils import misc

blueprint = blueprints.Blueprint("identity", __name__)

acl_module_check = misc.load_module(settings.ACL_MODULE)


def _build_oidc_config():
    if not settings.OIDC_AUTHORITY:
        return None

    authority = settings.OIDC_AUTHORITY.rstrip("/")
    authority_url = urlparse(authority)
    authority_origin = f"{authority_url.scheme}://{authority_url.netloc}"
    authority_path = authority_url.path.rstrip("/")
    authorize_endpoint = f"{authority_origin}/application/o/authorize/"
    token_endpoint = f"{authority_origin}/application/o/token/"
    userinfo_endpoint = f"{authority_origin}/application/o/userinfo/"
    jwks_uri = settings.JWKS_URL or f"{authority_origin}{authority_path}/jwks/"
    end_session_endpoint = f"{authority_origin}{authority_path}/end-session/"
    metadata = {
        "issuer": authority,
        "authorization_endpoint": authorize_endpoint,
        "token_endpoint": token_endpoint,
        "userinfo_endpoint": userinfo_endpoint,
        "jwks_uri": jwks_uri,
        "end_session_endpoint": end_session_endpoint,
    }
    return {
        "authority": authority,
        "client_id": settings.OIDC_CLIENT_ID,
        "redirect_uri": settings.OIDC_REDIRECT_URI,
        "scope": settings.OIDC_SCOPE,
        "metadata": metadata,
    }


@blueprint.route("/v1/login", methods=["GET", "POST"])
def login():
    """Legacy login endpoint.

    Browser authentication is now handled by the frontend OIDC client, so this
    route simply redirects back to the SPA entrypoint.
    """
    return authnz.log_in()


@blueprint.route("/v1/auth_config", methods=["GET"])
def get_auth_config():
    return jsonify(
        {
            "auth_required": settings.USE_AUTH,
            "oidc": _build_oidc_config(),
        }
    )


@blueprint.route("/v1/client_config", methods=["GET"])
@authnz.require_auth
def get_client_config():
    """
    Get configuration to help clients bootstrap themselves.

    .. :quickref: Client Configuration; Get configuration to help clients
                  bootstrap themselves.

    **Example request**:

    .. sourcecode:: http

       GET /v1/client_config HTTP/1.1

    **Example response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
       Content-Type: application/json

       {
         "defined": {},
         "generated": {
           "xsrf_cookie_name": "XSRF_COOKIE",
            "maintenance_mode": false,
            "history_page_limit": 500,
           "permissions": {
             "list": true,
             "create": true
           }
         }
       }

    :resheader Content-Type: application/json
    :statuscode 200: Success
    """
    permissions = {
        "secrets": {
            "list": acl_module_check(
                resource_type="secret",
                action="list",
                resource_id="*",
            ),
            "create": acl_module_check(
                resource_type="secret",
                action="create",
                resource_id="*",
            ),
        },
        "groups": {
            "list": acl_module_check(resource_type="group", action="list"),
            "create": acl_module_check(
                resource_type="group",
                action="create",
            ),
        },
    }
    tags = set()
    tags.update(settings.TAGS_EXCLUDING_ROTATION)
    tags.update(settings.ROTATION_DAYS_CONFIG.keys())
    response = jsonify(
        {
            "defined": settings.CLIENT_CONFIG,
            "generated": {
                "auth_required": settings.USE_AUTH,
                "oidc": _build_oidc_config(),
                "xsrf_cookie_name": "",
                "maintenance_mode": settings.MAINTENANCE_MODE,
                "history_page_limit": settings.HISTORY_PAGE_LIMIT,
                "defined_tags": list(tags),
                "permissions": permissions,
            },
        }
    )
    return response


@blueprint.route("/v1/user/email", methods=["GET", "POST"])
@authnz.require_auth
def get_user_info():
    try:
        email = authnz.get_logged_in_email() or authnz.get_logged_in_user()
        response = jsonify({"email": email})
    except authnz.UserUnknownError:
        response = jsonify({"email": None})
    return response
