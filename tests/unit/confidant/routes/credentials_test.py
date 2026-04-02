from datetime import datetime, timezone

from confidant.app import create_app
from confidant.schema.credentials import CredentialResponse
from confidant.schema.credentials import CredentialsResponse
from confidant.schema.credentials import RevisionsResponse
from confidant.schema.services import ServiceResponse
from confidant.routes import credentials as credentials_routes


def _credential(
    credential_id="c1",
    revision=1,
    name="Test credential",
    credential_pairs=None,
):
    return CredentialResponse(
        tenant_id="singletenant",
        id=credential_id,
        name=name,
        revision=revision,
        enabled=True,
        modified_date=datetime.now(timezone.utc),
        modified_by="user@example.com",
        credential_keys=["api_key"],
        credential_pairs={"api_key": "value"} if credential_pairs is None else credential_pairs,
    )


def _service(service_id="service-a", credentials=None):
    return ServiceResponse(
        tenant_id="singletenant",
        id=service_id,
        revision=1,
        enabled=True,
        modified_date=datetime.now(timezone.utc),
        modified_by="user@example.com",
        credentials=credentials or ["c1"],
    )


def test_service_can_access_mapped_credential(mocker):
    mocker.patch("confidant.settings.USE_AUTH", True)
    mocker.patch(
        "confidant.routes.credentials.authnz.user_is_user_type",
        side_effect=lambda user_type: user_type == "service",
    )
    mocker.patch(
        "confidant.routes.credentials.authnz.get_logged_in_user",
        return_value="service-a",
    )
    mocker.patch(
        "confidant.routes.credentials.servicemanager.get_service_latest",
        return_value=_service(),
    )

    assert credentials_routes._service_has_credential_access("singletenant", "c1") is True
    assert credentials_routes._service_has_credential_access("singletenant", "c2") is False
def test_can_read_credential_falls_back_to_service_mapping(mocker):
    mocker.patch("confidant.routes.credentials.acl_module_check", return_value=False)
    mocker.patch(
        "confidant.routes.credentials._service_has_credential_access",
        return_value=True,
    )

    assert credentials_routes._can_read_credential("singletenant", "c1", "read") is True


def test_read_action_for_request_defaults_to_read_with_alert(mocker):
    mocker.patch("confidant.settings.USE_AUTH", False)

    assert credentials_routes._read_action_for_request() == "read_with_alert"
    assert credentials_routes._should_alert_on_read() is True


def test_read_action_for_service_request_is_read(mocker):
    mocker.patch("confidant.settings.USE_AUTH", True)
    mocker.patch(
        "confidant.routes.credentials.authnz.user_is_user_type",
        side_effect=lambda user_type: user_type == "service",
    )

    assert credentials_routes._read_action_for_request() == "read"
    assert credentials_routes._should_alert_on_read() is False


def test_metadata_access_allows_read_permissions(mocker):
    acl_mock = mocker.patch(
        "confidant.routes.credentials.acl_module_check",
        side_effect=[False, True],
    )
    mocker.patch(
        "confidant.routes.credentials._service_has_credential_access",
        return_value=False,
    )

    assert credentials_routes._can_view_credential_metadata("singletenant", "c1") is True
    assert acl_mock.call_args_list[0].kwargs["action"] == "metadata"
    assert acl_mock.call_args_list[1].kwargs["action"] == "read"


def test_get_credential_list(mocker):
    app = create_app()
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch("confidant.routes.credentials.authnz.get_logged_in_user", return_value="user@example.com")
    mocker.patch("confidant.routes.credentials.acl_module_check", return_value=True)
    mocker.patch(
        "confidant.routes.credentials.credentialmanager.list_credentials",
        return_value=CredentialsResponse(credentials=[_credential()]),
    )

    ret = app.test_client().get("/v1/credentials")
    assert ret.status_code == 200
    body = ret.get_json()
    assert body["credentials"][0]["tenant_id"] == "singletenant"
    assert body["credentials"][0]["id"] == "c1"


def test_get_credential_list_uses_auth_tenant(mocker):
    app = create_app()
    mocker.patch("confidant.settings.MULTI_TENANT", True)
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch("confidant.routes.credentials.authnz.get_logged_in_user", return_value="user@example.com")
    mocker.patch("confidant.routes.credentials.authnz.get_tenant_id", return_value="tenant-a")
    mocker.patch("confidant.routes.credentials.acl_module_check", return_value=True)
    list_mock = mocker.patch(
        "confidant.routes.credentials.credentialmanager.list_credentials",
        return_value=CredentialsResponse(credentials=[_credential()]),
    )

    ret = app.test_client().get("/v1/credentials")
    assert ret.status_code == 200
    list_mock.assert_called_once_with("tenant-a", limit=None, page=None)


def test_get_credential_detail_and_metadata_only(mocker):
    app = create_app()
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch("confidant.routes.credentials.authnz.get_logged_in_user", return_value="user@example.com")
    mocker.patch("confidant.routes.credentials.acl_module_check", return_value=True)
    latest_mock = mocker.patch(
        "confidant.routes.credentials.credentialmanager.get_credential_latest",
        return_value=_credential(),
    )

    ret = app.test_client().get(
        "/v1/credentials/c1?metadata_only=false"
    )
    assert ret.status_code == 200
    body = ret.get_json()
    assert body["credential_pairs"] == {"api_key": "value"}
    assert body["permissions"]["read_with_alert"] is True
    assert body["permissions"]["read"] is False
    latest_mock.assert_any_call(
        "singletenant",
        "c1",
        metadata_only=False,
        alert_on_access=True,
    )

    ret = app.test_client().get(
        "/v1/credentials/c1?metadata_only=true"
    )
    assert ret.status_code == 200
    body = ret.get_json()
    assert body["credential_pairs"] == {}
    assert body["permissions"]["read"] is False
    assert body["permissions"]["read_with_alert"] is False
    latest_mock.assert_any_call(
        "singletenant",
        "c1",
        metadata_only=True,
        alert_on_access=False,
    )


def test_service_full_reads_do_not_alert(mocker):
    mocker.patch("confidant.settings.USE_AUTH", True)
    mocker.patch(
        "confidant.routes.credentials.authnz.user_is_user_type",
        side_effect=lambda user_type: user_type == "service",
    )

    assert credentials_routes._read_action_for_request() == "read"
    assert credentials_routes._should_alert_on_read() is False


def test_get_credential_dependencies_allows_read_permissions(mocker):
    app = create_app()
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch(
        "confidant.routes.credentials.authnz.get_logged_in_user",
        return_value="user@example.com",
    )
    mocker.patch(
        "confidant.routes.credentials._can_view_credential_metadata",
        return_value=True,
    )
    deps_mock = mocker.patch(
        "confidant.routes.credentials.credentialmanager.get_credential_dependencies",
        return_value=[{"id": "service-a", "enabled": True}],
    )

    ret = app.test_client().get("/v1/credentials/c1/services")
    assert ret.status_code == 200
    assert ret.get_json()["services"][0]["id"] == "service-a"
    deps_mock.assert_called_once_with("singletenant", "c1")


def test_create_and_update_credential(mocker):
    app = create_app()
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch("confidant.routes.credentials.authnz.get_logged_in_user", return_value="user@example.com")
    mocker.patch("confidant.routes.credentials.acl_module_check", return_value=True)
    mocker.patch(
        "confidant.routes.credentials.credentialmanager.create_credential",
        return_value=(_credential(), None),
    )
    mocker.patch(
        "confidant.routes.credentials.credentialmanager.update_credential",
        return_value=(_credential(revision=2), None),
    )

    ret = app.test_client().post(
        "/v1/credentials",
        json={
            "name": "Test credential",
            "credential_pairs": {"API_KEY": "value"},
        },
    )
    assert ret.status_code == 200
    assert ret.get_json()["revision"] == 1

    ret = app.test_client().put(
        "/v1/credentials/c1",
        json={
            "name": "Test credential",
        },
    )
    assert ret.status_code == 200
    assert ret.get_json()["revision"] == 2


def test_list_and_get_versions(mocker):
    app = create_app()
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch("confidant.routes.credentials.authnz.get_logged_in_user", return_value="user@example.com")
    mocker.patch("confidant.routes.credentials.acl_module_check", return_value=True)
    mocker.patch(
        "confidant.routes.credentials.credentialmanager.list_credential_versions",
        return_value=RevisionsResponse(versions=[_credential(), _credential(revision=2)]),
    )
    version_mock = mocker.patch(
        "confidant.routes.credentials.credentialmanager.get_credential_version",
        return_value=_credential(revision=2),
    )

    ret = app.test_client().get(
        "/v1/credentials/c1/versions"
    )
    assert ret.status_code == 200
    assert [v["revision"] for v in ret.get_json()["versions"]] == [1, 2]

    ret = app.test_client().get(
        "/v1/credentials/c1/versions/2"
    )
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
