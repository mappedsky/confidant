from datetime import datetime, timezone

from confidant.app import create_app
from confidant.schema.services import ServiceResponse
from confidant.schema.services import ServicesResponse
from confidant.schema.services import RevisionsResponse


def _service(service_id="s1", revision=1, credentials=None):
    return ServiceResponse(
        tenant_id="singletenant",
        id=service_id,
        revision=revision,
        enabled=True,
        modified_date=datetime.now(timezone.utc),
        modified_by="user@example.com",
        account=None,
        credentials=credentials or ["c1"],
    )


def test_get_services_list(mocker):
    app = create_app()
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch("confidant.routes.services.authnz.get_logged_in_user", return_value="user@example.com")
    mocker.patch("confidant.routes.services.acl_module_check", return_value=True)
    mocker.patch(
        "confidant.routes.services.servicemanager.list_services",
        return_value=ServicesResponse(services=[_service(), _service("s2")]),
    )

    ret = app.test_client().get("/v1/services")
    assert ret.status_code == 200
    assert [s["id"] for s in ret.get_json()["services"]] == ["s1", "s2"]
    assert ret.get_json()["services"][0]["tenant_id"] == "singletenant"


def test_get_service_detail(mocker):
    app = create_app()
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch("confidant.routes.services.authnz.get_logged_in_user", return_value="user@example.com")
    mocker.patch("confidant.routes.services.acl_module_check", return_value=True)
    mocker.patch(
        "confidant.routes.services.servicemanager.get_service_latest",
        return_value=_service(),
    )

    ret = app.test_client().get("/v1/services/s1")
    assert ret.status_code == 200
    body = ret.get_json()
    assert body["credentials"] == ["c1"]
    assert body["permissions"]["get"] is True


def test_get_service_versions_and_version_detail(mocker):
    app = create_app()
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch("confidant.routes.services.authnz.get_logged_in_user", return_value="user@example.com")
    mocker.patch("confidant.routes.services.acl_module_check", return_value=True)
    mocker.patch(
        "confidant.routes.services.servicemanager.list_service_versions",
        return_value=RevisionsResponse(versions=[_service(), _service(revision=2)]),
    )
    mocker.patch(
        "confidant.routes.services.servicemanager.get_service_version",
        return_value=_service(revision=2),
    )
    mocker.patch(
        "confidant.routes.services.servicemanager.store.list_services",
        return_value={"Items": []},
    )

    ret = app.test_client().get("/v1/services/s1/versions")
    assert ret.status_code == 200
    assert [s["revision"] for s in ret.get_json()["versions"]] == [1, 2]

    ret = app.test_client().get(
        "/v1/services/s1/versions/2"
    )
    assert ret.status_code == 200
    body = ret.get_json()
    assert body["revision"] == 2
    assert body["credentials"] == ["c1"]


def test_create_and_update_service(mocker):
    app = create_app()
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch("confidant.routes.services.authnz.get_logged_in_user", return_value="user@example.com")
    mocker.patch("confidant.routes.services.acl_module_check", return_value=True)
    mocker.patch(
        "confidant.routes.services.servicemanager.get_service_latest",
        side_effect=[None, _service()],
    )
    mocker.patch(
        "confidant.routes.services.servicemanager.create_service",
        return_value=(_service(), None),
    )
    mocker.patch(
        "confidant.routes.services.servicemanager.update_service",
        return_value=(_service(revision=2), None),
    )
    mocker.patch(
        "confidant.routes.services.credentialmanager.get_credentials",
        return_value=[type("Cred", (), {"id": "c1"})()],
    )
    mocker.patch(
        "confidant.routes.services.servicemanager.store.list_services",
        return_value={"Items": []},
    )

    ret = app.test_client().put(
        "/v1/services/s1",
        json={
            "credentials": ["c1"],
        },
    )
    assert ret.status_code == 200
    assert ret.get_json()["revision"] == 1
    assert ret.get_json()["credentials"] == ["c1"]

    ret = app.test_client().put(
        "/v1/services/s1",
        json={
            "credentials": ["c1"],
        },
    )
    assert ret.status_code == 200
    assert ret.get_json()["revision"] == 2
    assert ret.get_json()["credentials"] == ["c1"]
