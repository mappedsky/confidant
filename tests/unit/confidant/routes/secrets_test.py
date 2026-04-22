import logging
from datetime import datetime, timezone

from confidant.app import create_app
from confidant.routes import secrets as secret_routes
from confidant.schema.secrets import RevisionsResponse, SecretResponse, SecretsResponse


def _secret(secret_id="c1", revision=1, name="Test secret", secret_pairs=None):
    if secret_pairs is None:
        secret_pairs = {"api_key": "value"}
    return SecretResponse(
        tenant_id="singletenant",
        id=secret_id,
        name=name,
        revision=revision,
        modified_date=datetime.now(timezone.utc),
        modified_by="user@example.com",
        secret_keys=["api_key"],
        secret_pairs=secret_pairs,
    )


def test_can_decrypt_secret_uses_acl_only(mocker):
    mocker.patch(
        "confidant.routes.secrets.acl_module_check",
        return_value=True,
    )

    assert secret_routes._can_decrypt_secret("singletenant", "c1") is True


def test_metadata_access_allows_decrypt_permissions(mocker):
    acl_mock = mocker.patch(
        "confidant.routes.secrets.acl_module_check",
        side_effect=[False, True],
    )

    assert secret_routes._can_view_secret_metadata("singletenant", "c1") is True
    assert acl_mock.call_args_list[0].kwargs["action"] == "metadata"
    assert acl_mock.call_args_list[1].kwargs["action"] == "decrypt"


def test_get_secret_list(mocker):
    app = create_app()
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch(
        "confidant.routes.secrets.authnz.get_logged_in_user",
        return_value="user@example.com",
    )
    acl_mock = mocker.patch(
        "confidant.routes.secrets.acl_module_check", return_value=True
    )
    mocker.patch(
        "confidant.routes.secrets.secretmanager.list_secrets",
        return_value=SecretsResponse(secrets=[_secret()]),
    )

    ret = app.test_client().get("/v1/secrets")
    assert ret.status_code == 200
    body = ret.get_json()
    assert body["secrets"][0]["tenant_id"] == "singletenant"
    assert body["secrets"][0]["id"] == "c1"
    assert acl_mock.call_args.kwargs["resource_id"] == "c1"


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
    list_mock.assert_called_once_with(
        "tenant-a",
        limit=None,
        page=None,
        prefix=None,
    )


def test_get_secret_list_passes_prefix(mocker):
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
    mocker.patch(
        "confidant.routes.secrets.acl_module_check",
        return_value=True,
    )
    list_mock = mocker.patch(
        "confidant.routes.secrets.secretmanager.list_secrets",
        return_value=SecretsResponse(secrets=[_secret()]),
    )

    ret = app.test_client().get("/v1/secrets?prefix=apps/")

    assert ret.status_code == 200
    list_mock.assert_called_once_with(
        "tenant-a",
        limit=None,
        page=None,
        prefix="apps/",
    )


def test_get_secret_list_filters_by_path_acl(mocker):
    app = create_app()
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch(
        "confidant.routes.secrets.authnz.get_logged_in_user",
        return_value="user@example.com",
    )
    acl_mock = mocker.patch(
        "confidant.routes.secrets.acl_module_check",
        side_effect=lambda **kwargs: kwargs["resource_id"] == "apps/test",
    )
    mocker.patch(
        "confidant.routes.secrets.secretmanager.list_secrets",
        return_value=SecretsResponse(
            secrets=[_secret("apps/test"), _secret("other/test")],
        ),
    )

    ret = app.test_client().get("/v1/secrets")
    assert ret.status_code == 200
    body = ret.get_json()
    assert [secret["id"] for secret in body["secrets"]] == ["apps/test"]
    assert acl_mock.call_count == 2


def test_get_secret_detail_and_explicit_decrypt(mocker):
    app = create_app()
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch(
        "confidant.routes.secrets.authnz.get_logged_in_user",
        return_value="user@example.com",
    )
    mocker.patch("confidant.routes.secrets.acl_module_check", return_value=True)
    latest_mock = mocker.patch(
        "confidant.routes.secrets.secretmanager.get_secret_latest",
        side_effect=lambda *args, **kwargs: _secret(),
    )

    ret = app.test_client().get("/v1/secrets/c1")
    assert ret.status_code == 200
    body = ret.get_json()
    assert body["secret_pairs"] == {}
    assert body["permissions"]["decrypt"] is True
    assert body["permissions"]["delete"] is True
    latest_mock.assert_any_call(
        "singletenant",
        "c1",
        metadata_only=True,
        alert_on_access=False,
    )

    latest_mock.reset_mock()
    ret = app.test_client().post("/v1/secrets/c1/decrypt")
    assert ret.status_code == 200
    body = ret.get_json()
    assert body["secret_pairs"] == {"api_key": "value"}
    assert body["permissions"]["decrypt"] is True
    assert body["permissions"]["delete"] is True
    latest_mock.assert_called_once_with(
        "singletenant",
        "c1",
        metadata_only=False,
        alert_on_access=True,
    )


def test_decrypt_secret_emits_audit_log(caplog, mocker):
    app = create_app()
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch(
        "confidant.routes.secrets.acl_module_check",
        return_value=True,
    )
    mocker.patch(
        "confidant.routes.secrets.secretmanager.get_secret_latest",
        return_value=_secret(),
    )

    with caplog.at_level(logging.INFO, logger="confidant.audit"):
        ret = app.test_client().post("/v1/secrets/c1/decrypt")

    assert ret.status_code == 200
    record = next(
        record for record in caplog.records if record.name == "confidant.audit"
    )
    assert record.event == "audit"
    assert record.action == "decrypt"
    assert record.resource_type == "secret"
    assert record.resource_id == "c1"
    assert record.outcome == "success"
    assert record.secret_key_count == 1


def test_get_secret_dependencies_allows_decrypt_permissions(mocker):
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
        return_value=[{"id": "service-a"}],
    )

    ret = app.test_client().get("/v1/secrets/c1/groups")
    assert ret.status_code == 200
    assert ret.get_json()["groups"][0]["id"] == "service-a"
    deps_mock.assert_called_once_with("singletenant", "c1")


def test_generate_value(mocker):
    app = create_app()
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch(
        "confidant.routes.secrets.stdlib_secrets.choice",
        side_effect=lambda charset: charset[0],
    )
    mocker.patch("confidant.routes.secrets.stdlib_secrets.SystemRandom.shuffle")

    ret = app.test_client().get(
        "/v1/value_generator?length=6&complexity=lowercase&complexity=digits",
    )

    assert ret.status_code == 200
    assert ret.get_json() == {"value": "a0aaaa"}


def test_generate_value_rejects_invalid_complexity(mocker):
    app = create_app()
    mocker.patch("confidant.settings.USE_AUTH", False)

    ret = app.test_client().get("/v1/value_generator?complexity=emoji")

    assert ret.status_code == 400
    assert "complexity" in ret.get_json()["error"]


def test_generate_value_rejects_invalid_length(mocker):
    app = create_app()
    mocker.patch("confidant.settings.USE_AUTH", False)

    ret = app.test_client().get("/v1/value_generator?length=not-a-number")

    assert ret.status_code == 400
    assert "length" in ret.get_json()["error"]


def test_create_and_update_secret(mocker):
    app = create_app()
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch(
        "confidant.routes.secrets.authnz.get_logged_in_user",
        return_value="user@example.com",
    )
    mocker.patch("confidant.routes.secrets.acl_module_check", return_value=True)
    create_mock = mocker.patch(
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
            "id": "apps/test",
            "name": "Test secret",
            "secret_pairs": {"API_KEY": "value"},
        },
    )
    assert ret.status_code == 200
    assert ret.get_json()["revision"] == 1
    assert create_mock.call_args.kwargs["secret_id"] == "apps/test"

    ret = app.test_client().put(
        "/v1/secrets/c1",
        json={
            "name": "Test secret",
        },
    )
    assert ret.status_code == 200
    assert ret.get_json()["revision"] == 2


def test_create_secret_checks_path_based_acl(mocker):
    app = create_app()
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch(
        "confidant.routes.secrets.authnz.get_logged_in_user",
        return_value="user@example.com",
    )
    acl_mock = mocker.patch(
        "confidant.routes.secrets.acl_module_check", return_value=True
    )
    mocker.patch(
        "confidant.routes.secrets.secretmanager.create_secret",
        return_value=(_secret(), None),
    )

    ret = app.test_client().post(
        "/v1/secrets",
        json={
            "id": "apps/test",
            "name": "Test secret",
            "secret_pairs": {"API_KEY": "value"},
        },
    )

    assert ret.status_code == 200
    create_call = None
    for acl_call in acl_mock.call_args_list:
        if acl_call.kwargs["action"] == "create":
            create_call = acl_call
            break
    assert create_call is not None
    assert create_call.kwargs["resource_id"] == "apps/test"


def test_create_secret_rejects_invalid_id(mocker):
    app = create_app()
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch("confidant.routes.secrets.acl_module_check", return_value=True)
    ret = app.test_client().post(
        "/v1/secrets",
        json={
            "id": "apps/test/",
            "name": "Test secret",
            "secret_pairs": {"API_KEY": "value"},
        },
    )
    assert ret.status_code == 400
    assert ret.get_json()["error"] == "secret id must not end with /"


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
        side_effect=lambda *args, **kwargs: (
            _secret(revision=2, secret_pairs={})
            if kwargs.get("metadata_only")
            else _secret(revision=2)
        ),
    )

    ret = app.test_client().get("/v1/secrets/c1/versions")
    assert ret.status_code == 200
    assert [v["revision"] for v in ret.get_json()["versions"]] == [1, 2]

    ret = app.test_client().get("/v1/secrets/c1/versions/2")
    assert ret.status_code == 200
    body = ret.get_json()
    assert body["revision"] == 2
    assert body["secret_pairs"] == {}
    assert body["permissions"]["decrypt"] is True
    assert body["permissions"]["delete"] is True
    version_mock.assert_called_once_with(
        "singletenant",
        "c1",
        2,
        metadata_only=True,
    )

    version_mock.reset_mock()
    ret = app.test_client().post("/v1/secrets/c1/versions/2/decrypt")
    assert ret.status_code == 200
    body = ret.get_json()
    assert body["revision"] == 2
    assert body["secret_pairs"] == {"api_key": "value"}
    assert body["permissions"]["decrypt"] is True
    version_mock.assert_called_once_with(
        "singletenant",
        "c1",
        2,
        metadata_only=False,
        alert_on_access=True,
    )


def test_delete_secret(mocker):
    app = create_app()
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch(
        "confidant.routes.secrets.authnz.get_logged_in_user",
        return_value="user@example.com",
    )
    acl_mock = mocker.patch(
        "confidant.routes.secrets.acl_module_check",
        return_value=True,
    )
    delete_mock = mocker.patch(
        "confidant.routes.secrets.secretmanager.delete_secret",
        return_value=(_secret(), None),
    )

    ret = app.test_client().delete("/v1/secrets/c1")

    assert ret.status_code == 200
    delete_mock.assert_called_once_with(
        tenant_id="singletenant",
        secret_id="c1",
    )
    assert acl_mock.call_args.kwargs["action"] == "delete"


def test_delete_secret_conflict(mocker):
    app = create_app()
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch(
        "confidant.routes.secrets.authnz.get_logged_in_user",
        return_value="user@example.com",
    )
    mocker.patch(
        "confidant.routes.secrets.acl_module_check",
        return_value=True,
    )
    mocker.patch(
        "confidant.routes.secrets.secretmanager.delete_secret",
        return_value=(
            None,
            {
                "error": "Secret is still mapped to groups.",
                "groups": ["service-a"],
            },
        ),
    )

    ret = app.test_client().delete("/v1/secrets/c1")

    assert ret.status_code == 409
    assert ret.get_json()["groups"] == ["service-a"]


def test_delete_secret_conflict_emits_audit_log(caplog, mocker):
    app = create_app()
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch(
        "confidant.routes.secrets.acl_module_check",
        return_value=True,
    )
    mocker.patch(
        "confidant.routes.secrets.secretmanager.delete_secret",
        return_value=(
            None,
            {
                "error": "Secret is still mapped to groups.",
                "groups": ["service-a"],
            },
        ),
    )

    with caplog.at_level(logging.INFO, logger="confidant.audit"):
        ret = app.test_client().delete("/v1/secrets/c1")

    assert ret.status_code == 409
    record = next(
        record for record in caplog.records if record.name == "confidant.audit"
    )
    assert record.action == "delete"
    assert record.resource_type == "secret"
    assert record.resource_id == "c1"
    assert record.outcome == "conflict"
    assert record.groups == ["service-a"]
