from datetime import datetime, timezone

from confidant.app import create_app
from confidant.schema.credentials import CredentialResponse
from confidant.schema.credentials import CredentialsResponse
from confidant.schema.credentials import RevisionsResponse


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
    mocker.patch(
        "confidant.routes.credentials.credentialmanager.get_credential_latest",
        return_value=_credential(),
    )

    ret = app.test_client().get(
        "/v1/credentials/c1?metadata_only=false"
    )
    assert ret.status_code == 200
    body = ret.get_json()
    assert body["credential_pairs"] == {"api_key": "value"}
    assert body["permissions"]["get"] is True

    ret = app.test_client().get(
        "/v1/credentials/c1?metadata_only=true"
    )
    assert ret.status_code == 200
    body = ret.get_json()
    assert body["credential_pairs"] == {}
    assert body["permissions"]["get"] is False


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
    mocker.patch(
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
    assert ret.get_json()["revision"] == 2
