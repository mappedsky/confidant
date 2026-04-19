import pytest
from pytest_mock.plugin import MockerFixture
from werkzeug.exceptions import InternalServerError
from werkzeug.exceptions import Unauthorized

from confidant import authnz
from confidant.app import create_app


def test_get_logged_in_user_requires_principal(mocker: MockerFixture):
    mocker.patch("confidant.authnz.settings.USE_AUTH", True)
    app = create_app()
    with app.test_request_context("/v1/user/email"):
        with pytest.raises(authnz.UserUnknownError):
            authnz.get_logged_in_user()


def test_get_logged_in_user_from_request_principal(mocker: MockerFixture):
    mocker.patch("confidant.authnz.settings.USE_AUTH", True)
    app = create_app()
    with app.test_request_context("/v1/user/email"):
        principal = authnz.RequestPrincipal(
            user_type="user",
            username="user@example.com",
            email="user@example.com",
            tenant_id="tenant-a",
            group_ids=["engineering"],
            jwt_claims={},
        )
        authnz._set_request_principal(principal)
        assert authnz.get_logged_in_user() == "user@example.com"
        assert authnz.get_logged_in_email() == "user@example.com"
        assert authnz.get_logged_in_group_ids() == ["engineering"]


def test_get_tenant_id_singletenant_default(mocker: MockerFixture):
    mocker.patch("confidant.authnz.settings.MULTI_TENANT", False)
    app = create_app()
    with app.app_context():
        assert authnz.get_tenant_id() == "singletenant"


def test_get_tenant_id_from_auth_context(mocker: MockerFixture):
    mocker.patch("confidant.authnz.settings.MULTI_TENANT", True)
    app = create_app()
    with app.app_context():
        g_mock = mocker.patch("confidant.authnz.g")
        g_mock.tenant_id = "tenant-a"
        assert authnz.get_tenant_id() == "tenant-a"


def test_get_tenant_id_rejects_missing_tenant(mocker: MockerFixture):
    mocker.patch("confidant.authnz.settings.MULTI_TENANT", True)
    app = create_app()
    with app.app_context():
        g_mock = mocker.patch("confidant.authnz.g")
        g_mock.tenant_id = None
        with pytest.raises(authnz.UserUnknownError):
            authnz.get_tenant_id()


def test_user_is_user_type(mocker: MockerFixture):
    mocker.patch("confidant.authnz.settings.USE_AUTH", False)
    assert authnz.user_is_user_type("anything") is True

    mocker.patch("confidant.authnz.settings.USE_AUTH", True)
    app = create_app()
    with app.app_context():
        g_mock = mocker.patch("confidant.authnz.g")
        g_mock.user_type = "user"
        assert authnz.user_is_user_type("user") is True
        assert authnz.user_is_user_type("service") is False


def test_user_is_service(mocker: MockerFixture):
    mocker.patch("confidant.authnz.settings.USE_AUTH", False)
    assert authnz.user_is_service("anything") is True

    mocker.patch("confidant.authnz.settings.USE_AUTH", True)
    mocker.patch("confidant.authnz.settings.JWT_SERVICE_TYPE_VALUE", "service")
    app = create_app()
    with app.app_context():
        g_mock = mocker.patch("confidant.authnz.g")
        g_mock.user_type = "service"
        g_mock.username = "confidant-unittest"
        assert authnz.user_is_service("confidant-unittest") is True
        assert authnz.user_is_service("other-service") is False


def test_redirect_to_logout_if_no_auth_is_noop():
    def mock_fn():
        return "ok"

    wrapped = authnz.redirect_to_logout_if_no_auth(mock_fn)
    assert wrapped() == "ok"


def test_require_logout_for_goodbye_is_noop():
    def mock_fn():
        return "ok"

    wrapped = authnz.require_logout_for_goodbye(mock_fn)
    assert wrapped() == "ok"


def test_log_in_redirects_to_index():
    app = create_app()
    with app.test_request_context("/v1/login"):
        response = authnz.log_in()
        assert response.status_code == 302
        assert response.location == "/"


def test_read_bearer_token_from_authorization_header(mocker: MockerFixture):
    mocker.patch("confidant.authnz.settings.JWT_HEADER_NAME", "Authorization")
    app = create_app()
    with app.test_request_context(
        "/v1/user/email",
        headers={"Authorization": "Bearer test-token"},
    ):
        assert authnz._read_bearer_token_from_request() == "test-token"


def test_read_bearer_token_from_custom_header(mocker: MockerFixture):
    mocker.patch("confidant.authnz.settings.JWT_HEADER_NAME", "X-IDP-JWT")
    app = create_app()
    with app.test_request_context(
        "/v1/user/email",
        headers={"X-IDP-JWT": "test-token"},
    ):
        assert authnz._read_bearer_token_from_request() == "test-token"


def test_principal_from_payload_uses_service_claims(mocker: MockerFixture):
    mocker.patch(
        "confidant.authnz.settings.JWT_PRINCIPAL_TYPE_CLAIM",
        "principal_type",
    )
    mocker.patch("confidant.authnz.settings.JWT_SERVICE_TYPE_VALUE", "service")
    mocker.patch("confidant.authnz.settings.JWT_USER_TYPE_VALUE", "user")
    mocker.patch(
        "confidant.authnz.settings.JWT_ALLOWED_PRINCIPAL_TYPES",
        ["user", "service"],
    )
    mocker.patch(
        "confidant.authnz.settings.JWT_SERVICE_PRINCIPAL_CLAIM", "service_name"
    )
    payload = {
        "principal_type": "service",
        "service_name": "confidant-api",
        "sub": "client-123",
        "groups": ["policy-a", "policy-b"],
    }

    principal = authnz._principal_from_payload(payload)
    assert principal.user_type == "service"
    assert principal.username == "confidant-api"
    assert principal.group_ids == ["policy-a", "policy-b"]


def test_principal_from_payload_rejects_invalid_group_claim(
    mocker: MockerFixture,
):
    mocker.patch(
        "confidant.authnz.settings.JWT_PRINCIPAL_TYPE_CLAIM",
        "principal_type",
    )
    mocker.patch("confidant.authnz.settings.JWT_SERVICE_TYPE_VALUE", "service")
    mocker.patch("confidant.authnz.settings.JWT_USER_TYPE_VALUE", "user")
    mocker.patch(
        "confidant.authnz.settings.JWT_ALLOWED_PRINCIPAL_TYPES",
        ["user", "service"],
    )
    mocker.patch(
        "confidant.authnz.settings.JWT_SERVICE_PRINCIPAL_CLAIM", "service_name"
    )
    payload = {
        "principal_type": "service",
        "service_name": "confidant-api",
        "sub": "client-123",
        "groups": "policy-a",
    }

    with pytest.raises(authnz.AuthenticationError):
        authnz._principal_from_payload(payload)


def test_decode_jwt_disables_audience_check_when_unset(mocker: MockerFixture):
    signing_key = mocker.Mock()
    signing_key.key = "public-key"
    jwks_client = mocker.Mock()
    jwks_client.get_signing_key_from_jwt.return_value = signing_key

    mocker.patch("confidant.authnz._get_jwks_client", return_value=jwks_client)
    decode_mock = mocker.patch(
        "confidant.authnz.jwt.decode", return_value={"sub": "developer"}
    )
    mocker.patch(
        "confidant.authnz.settings.ALLOWED_JWT_ALGORITHMS",
        ["RS256"],
    )
    mocker.patch("confidant.authnz.settings.JWT_ISSUER", "")
    mocker.patch("confidant.authnz.settings.JWT_AUDIENCE", "")

    payload = authnz._decode_jwt("token")

    assert payload == {"sub": "developer"}
    decode_mock.assert_called_once_with(
        "token",
        "public-key",
        algorithms=["RS256"],
        options={"verify_aud": False},
    )


def test_decode_jwt_validates_audience_when_configured(mocker: MockerFixture):
    signing_key = mocker.Mock()
    signing_key.key = "public-key"
    jwks_client = mocker.Mock()
    jwks_client.get_signing_key_from_jwt.return_value = signing_key

    mocker.patch("confidant.authnz._get_jwks_client", return_value=jwks_client)
    decode_mock = mocker.patch(
        "confidant.authnz.jwt.decode", return_value={"sub": "developer"}
    )
    mocker.patch(
        "confidant.authnz.settings.ALLOWED_JWT_ALGORITHMS",
        ["RS256"],
    )
    mocker.patch("confidant.authnz.settings.JWT_ISSUER", "")
    mocker.patch("confidant.authnz.settings.JWT_AUDIENCE", "confidant")

    payload = authnz._decode_jwt("token")

    assert payload == {"sub": "developer"}
    decode_mock.assert_called_once_with(
        "token",
        "public-key",
        algorithms=["RS256"],
        audience="confidant",
    )


def test_require_auth(mocker: MockerFixture):
    def mock_fn():
        return "ok"

    wrapped = authnz.require_auth(mock_fn)

    mocker.patch("confidant.authnz.settings.USE_AUTH", False)
    assert wrapped() == "ok"

    mocker.patch("confidant.authnz.settings.USE_AUTH", True)
    mocker.patch("confidant.authnz.settings.JWKS_URL", "")
    with pytest.raises(InternalServerError):
        wrapped()

    mocker.patch(
        "confidant.authnz.settings.JWKS_URL",
        "https://idp.example.com/jwks.json",
    )
    mocker.patch(
        "confidant.authnz._read_bearer_token_from_request",
        return_value=None,
    )
    with pytest.raises(Unauthorized):
        wrapped()

    mocker.patch(
        "confidant.authnz._read_bearer_token_from_request", return_value="token"
    )
    mocker.patch(
        "confidant.authnz._decode_jwt",
        side_effect=authnz.AuthenticationError("bad token"),
    )
    with pytest.raises(Unauthorized):
        wrapped()

    payload = {
        "principal_type": "service",
        "service_name": "confidant-api",
        "sub": "client-123",
        "email": "service@example.com",
        "tenant_id": "tenant-a",
        "groups": ["policy-a"],
    }
    mocker.patch(
        "confidant.authnz.settings.JWT_PRINCIPAL_TYPE_CLAIM",
        "principal_type",
    )
    mocker.patch(
        "confidant.authnz.settings.JWT_SERVICE_PRINCIPAL_CLAIM", "service_name"
    )
    mocker.patch("confidant.authnz.settings.JWT_SERVICE_TYPE_VALUE", "service")
    mocker.patch("confidant.authnz.settings.JWT_USER_TYPE_VALUE", "user")
    mocker.patch(
        "confidant.authnz.settings.JWT_ALLOWED_PRINCIPAL_TYPES",
        ["user", "service"],
    )
    mocker.patch("confidant.authnz.settings.JWT_EMAIL_CLAIM", "email")
    mocker.patch("confidant.authnz.settings.JWT_TENANT_ID_CLAIM", "tenant_id")
    mocker.patch("confidant.authnz.settings.JWT_SUB_CLAIM", "sub")
    mocker.patch("confidant.authnz._decode_jwt", return_value=payload)

    app = create_app()
    with app.app_context():
        assert wrapped() == "ok"
        assert authnz.g.user_type == "service"
        assert authnz.g.auth_type == "jwt"
        assert authnz.g.username == "confidant-api"
        assert authnz.g.tenant_id == "tenant-a"
        assert authnz.g.group_ids == ["policy-a"]
