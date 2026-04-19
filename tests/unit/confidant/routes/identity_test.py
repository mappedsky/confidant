from confidant.app import create_app
from confidant.authnz import UserUnknownError


def test_get_auth_config(mocker):
    mocker.patch("confidant.settings.USE_AUTH", True)
    mocker.patch(
        "confidant.settings.OIDC_AUTHORITY",
        "https://idp.example.com/application/o/confidant",
    )
    mocker.patch("confidant.settings.OIDC_CLIENT_ID", "confidant")
    mocker.patch(
        "confidant.settings.OIDC_REDIRECT_URI",
        "https://confidant.example.com/auth/callback",
    )
    mocker.patch("confidant.settings.OIDC_SCOPE", "openid email profile")
    mocker.patch("confidant.settings.JWKS_URL", "")
    app = create_app()
    ret = app.test_client().get("/v1/auth_config", follow_redirects=False)
    assert ret.status_code == 200
    assert ret.json["auth_required"] is True
    assert ret.json["oidc"]["client_id"] == "confidant"


def test_get_user_info(mocker):
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch(
        "confidant.routes.identity.authnz.get_logged_in_email",
        return_value="test@example.com",
    )
    app = create_app()
    ret = app.test_client().get("/v1/user/email", follow_redirects=False)
    assert ret.status_code == 200
    assert ret.json == {"email": "test@example.com"}


def test_get_user_info_no_user(mocker):
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch(
        "confidant.routes.identity.authnz.get_logged_in_user",
        side_effect=UserUnknownError(),
    )
    app = create_app()
    ret = app.test_client().get("/v1/user/email", follow_redirects=False)
    assert ret.status_code == 200
    assert ret.json == {"email": None}


def test_get_client_config(mocker):
    def acl_module_check(
        resource_type: str,
        action: str,
        resource_id: str | None = None,
    ) -> bool | None:
        if resource_type == "secret":
            if action == "create":
                return False
            if action == "list":
                return True
        elif resource_type == "group":
            if action == "create":
                return True
            if action == "list":
                return False
        return None

    mocker.patch("confidant.routes.identity.acl_module_check", acl_module_check)
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch("confidant.settings.MAINTENANCE_MODE", True)
    mocker.patch("confidant.settings.HISTORY_PAGE_LIMIT", 50)
    mocker.patch("confidant.settings.TAGS_EXCLUDING_ROTATION", [])
    mocker.patch("confidant.settings.ROTATION_DAYS_CONFIG", {})
    mocker.patch("confidant.settings.OIDC_AUTHORITY", "")
    mocker.patch("confidant.settings.OIDC_CLIENT_ID", "")
    mocker.patch("confidant.settings.OIDC_REDIRECT_URI", "")
    mocker.patch("confidant.settings.OIDC_SCOPE", "openid email")
    mocker.patch("confidant.settings.JWKS_URL", "")

    expected: dict[str, object] = {
        "generated": {
            "auth_required": False,
            "oidc": None,
            "maintenance_mode": True,
            "history_page_limit": 50,
            "defined_tags": [],
            "permissions": {
                "secrets": {
                    "list": True,
                    "create": False,
                },
                "groups": {
                    "list": False,
                    "create": True,
                },
            },
        },
    }

    app = create_app()
    ret = app.test_client().get("/v1/client_config", follow_redirects=False)
    assert ret.status_code == 200
    assert ret.json == expected
