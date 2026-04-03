from flask import blueprints
from flask import jsonify

from confidant import authnz
from confidant import settings
from confidant.utils import misc

blueprint = blueprints.Blueprint("identity", __name__)

acl_module_check = misc.load_module(settings.ACL_MODULE)


@blueprint.route("/v1/login", methods=["GET", "POST"])
def login():
    """Legacy login endpoint.

    Browser authentication is now handled by the frontend OIDC client, so this
    route simply redirects back to the SPA entrypoint.
    """
    return authnz.log_in()


@blueprint.route("/v1/auth_config", methods=["GET"])
def get_auth_config():
    oidc_config = None
    if settings.OIDC_AUTHORITY:
        oidc_config = {
            "authority": settings.OIDC_AUTHORITY,
            "client_id": settings.OIDC_CLIENT_ID,
            "redirect_uri": settings.OIDC_REDIRECT_URI,
            "scope": settings.OIDC_SCOPE,
        }
    return jsonify(
        {
            "auth_required": settings.USE_AUTH,
            "oidc": oidc_config,
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

       GET /v1/client_config

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
        "credentials": {
            "list": acl_module_check(resource_type="credential", action="list"),
            "create": acl_module_check(
                resource_type="credential",
                action="create",
            ),
        },
        "services": {
            "list": acl_module_check(resource_type="service", action="list"),
            "create": acl_module_check(
                resource_type="service",
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
                "oidc": (
                    {
                        "authority": settings.OIDC_AUTHORITY,
                        "client_id": settings.OIDC_CLIENT_ID,
                        "redirect_uri": settings.OIDC_REDIRECT_URI,
                        "scope": settings.OIDC_SCOPE,
                    }
                    if settings.OIDC_AUTHORITY
                    else None
                ),
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
