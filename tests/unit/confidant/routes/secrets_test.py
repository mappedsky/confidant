from datetime import datetime
from datetime import timezone

from confidant.app import create_app
from confidant.routes import secrets as secret_routes
from confidant.schema.groups import GroupResponse
from confidant.schema.secrets import RevisionsResponse
from confidant.schema.secrets import SecretResponse
from confidant.schema.secrets import SecretsResponse


def _secret(secret_id="c1", revision=1, name="Test secret", secret_pairs=None):
    if secret_pairs is None:
        secret_pairs = {"api_key": "value"}
    return SecretResponse(
        tenant_id="singletenant",
        id=secret_id,
        name=name,
        revision=revision,
        enabled=True,
        modified_date=datetime.now(timezone.utc),
        modified_by="user@example.com",
        secret_keys=["api_key"],
        secret_pairs=secret_pairs,
    )


def _group(group_id="service-a", secrets=None):
    return GroupResponse(
        tenant_id="singletenant",
        id=group_id,
        revision=1,
        enabled=True,
        modified_date=datetime.now(timezone.utc),
        modified_by="user@example.com",
        secrets=secrets or ["c1"],
    )


def test_service_can_access_mapped_secret(mocker):
    mocker.patch("confidant.settings.USE_AUTH", True)
    mocker.patch(
        "confidant.routes.secrets.authnz.user_is_user_type",
        side_effect=lambda user_type: user_type == "service",
    )
    mocker.patch(
        "confidant.routes.secrets.authnz.get_logged_in_user",
        return_value="service-a",
    )
    mocker.patch(
        "confidant.routes.secrets.groupmanager.get_group_latest",
        return_value=_group(),
    )

    has_access = secret_routes._service_has_secret_access("singletenant", "c1")
    assert has_access is True
    has_access = secret_routes._service_has_secret_access("singletenant", "c2")
    assert has_access is False


def test_can_read_secret_falls_back_to_service_mapping(mocker):
    mocker.patch(
        "confidant.routes.secrets.acl_module_check",
        return_value=False,
    )
    mocker.patch(
        "confidant.routes.secrets._service_has_secret_access",
        return_value=True,
    )

    assert secret_routes._can_read_secret("singletenant", "c1", "read") is True


def test_read_action_for_request_defaults_to_read_with_alert(mocker):
    mocker.patch("confidant.settings.USE_AUTH", False)

    assert secret_routes._read_action_for_request() == "read_with_alert"
    assert secret_routes._should_alert_on_read() is True


def test_read_action_for_service_request_is_read(mocker):
    mocker.patch("confidant.settings.USE_AUTH", True)
    mocker.patch(
        "confidant.routes.secrets.authnz.user_is_user_type",
        side_effect=lambda user_type: user_type == "service",
    )

    assert secret_routes._read_action_for_request() == "read"
    assert secret_routes._should_alert_on_read() is False


def test_metadata_access_allows_read_permissions(mocker):
    acl_mock = mocker.patch(
        "confidant.routes.secrets.acl_module_check",
        side_effect=[False, True],
    )
    mocker.patch(
        "confidant.routes.secrets._service_has_secret_access",
        return_value=False,
    )

    assert secret_routes._can_view_secret_metadata("singletenant", "c1") is True
    assert acl_mock.call_args_list[0].kwargs["action"] == "metadata"
    assert acl_mock.call_args_list[1].kwargs["action"] == "read"


def test_get_secret_list(mocker):
    app = create_app()
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch(
        "confidant.routes.secrets.authnz.get_logged_in_user",
        return_value="user@example.com",
    )
    mocker.patch("confidant.routes.secrets.acl_module_check", return_value=True)
    mocker.patch(
        "confidant.routes.secrets.secretmanager.list_secrets",
        return_value=SecretsResponse(secrets=[_secret()]),
    )

    ret = app.test_client().get("/v1/secrets")
    assert ret.status_code == 200
    body = ret.get_json()
    assert body["secrets"][0]["tenant_id"] == "singletenant"
    assert body["secrets"][0]["id"] == "c1"


def test_get_secret_list_uses_auth_tenant(mocker):
    app = create_app()
    mocker.patch("confidant.settings.MULTI_TENANT", True)
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch(
        "confidant.routes.secrets.authnz.get_logged_in_user",
        return_value="user@example.com",
    )
    mocker.patch(
        "confidant.routes.secrets.authnz.get_tenant_id",
        return_value="tenant-a",
    )
    mocker.patch("confidant.routes.secrets.acl_module_check", return_value=True)
    list_mock = mocker.patch(
        "confidant.routes.secrets.secretmanager.list_secrets",
        return_value=SecretsResponse(secrets=[_secret()]),
    )

    ret = app.test_client().get("/v1/secrets")
    assert ret.status_code == 200
    list_mock.assert_called_once_with("tenant-a", limit=None, page=None)


def test_get_secret_detail_and_metadata_only(mocker):
    app = create_app()
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch(
        "confidant.routes.secrets.authnz.get_logged_in_user",
        return_value="user@example.com",
    )
    mocker.patch("confidant.routes.secrets.acl_module_check", return_value=True)
    latest_mock = mocker.patch(
        "confidant.routes.secrets.secretmanager.get_secret_latest",
        return_value=_secret(),
    )

    ret = app.test_client().get("/v1/secrets/c1?metadata_only=false")
    assert ret.status_code == 200
    body = ret.get_json()
    assert body["secret_pairs"] == {"api_key": "value"}
    assert body["permissions"]["read_with_alert"] is True
    assert body["permissions"]["read"] is False
    latest_mock.assert_any_call(
        "singletenant",
        "c1",
        metadata_only=False,
        alert_on_access=True,
    )

    ret = app.test_client().get("/v1/secrets/c1?metadata_only=true")
    assert ret.status_code == 200
    body = ret.get_json()
    assert body["secret_pairs"] == {}
    assert body["permissions"]["read"] is False
    assert body["permissions"]["read_with_alert"] is False
    latest_mock.assert_any_call(
        "singletenant",
        "c1",
        metadata_only=True,
        alert_on_access=False,
    )


def test_get_secret_dependencies_allows_read_permissions(mocker):
    app = create_app()
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch(
        "confidant.routes.secrets.authnz.get_logged_in_user",
        return_value="user@example.com",
    )
    mocker.patch(
        "confidant.routes.secrets._can_view_secret_metadata",
        return_value=True,
    )
    deps_mock = mocker.patch(
        "confidant.routes.secrets.secretmanager.get_secret_dependencies",
        return_value=[{"id": "service-a", "enabled": True}],
    )

    ret = app.test_client().get("/v1/secrets/c1/groups")
    assert ret.status_code == 200
    assert ret.get_json()["groups"][0]["id"] == "service-a"
    deps_mock.assert_called_once_with("singletenant", "c1")


def test_create_and_update_secret(mocker):
    app = create_app()
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch(
        "confidant.routes.secrets.authnz.get_logged_in_user",
        return_value="user@example.com",
    )
    mocker.patch("confidant.routes.secrets.acl_module_check", return_value=True)
    mocker.patch(
        "confidant.routes.secrets.secretmanager.create_secret",
        return_value=(_secret(), None),
    )
    mocker.patch(
        "confidant.routes.secrets.secretmanager.update_secret",
        return_value=(_secret(revision=2), None),
    )

    ret = app.test_client().post(
        "/v1/secrets",
        json={
            "name": "Test secret",
            "secret_pairs": {"API_KEY": "value"},
        },
    )
    assert ret.status_code == 200
    assert ret.get_json()["revision"] == 1

    ret = app.test_client().put(
        "/v1/secrets/c1",
        json={
            "name": "Test secret",
        },
    )
    assert ret.status_code == 200
    assert ret.get_json()["revision"] == 2


def test_list_and_get_versions(mocker):
    app = create_app()
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch(
        "confidant.routes.secrets.authnz.get_logged_in_user",
        return_value="user@example.com",
    )
    mocker.patch("confidant.routes.secrets.acl_module_check", return_value=True)
    versions = [_secret(), _secret(revision=2)]
    mocker.patch(
        "confidant.routes.secrets.secretmanager.list_secret_versions",
        return_value=RevisionsResponse(versions=versions),
    )
    version_mock = mocker.patch(
        "confidant.routes.secrets.secretmanager.get_secret_version",
        return_value=_secret(revision=2),
    )

    ret = app.test_client().get("/v1/secrets/c1/versions")
    assert ret.status_code == 200
    assert [v["revision"] for v in ret.get_json()["versions"]] == [1, 2]

    ret = app.test_client().get("/v1/secrets/c1/versions/2")
    assert ret.status_code == 200
    body = ret.get_json()
    assert body["revision"] == 2
    assert body["permissions"]["read_with_alert"] is True
    version_mock.assert_called_once_with(
        "singletenant",
        "c1",
        2,
        alert_on_access=True,
    )
