from datetime import datetime
from datetime import timezone

from confidant.app import create_app
from confidant.schema.groups import GroupResponse
from confidant.schema.groups import GroupsResponse
from confidant.schema.groups import RevisionsResponse


def _group(group_id="s1", revision=1, secrets=None):
    return GroupResponse(
        tenant_id="singletenant",
        id=group_id,
        revision=revision,
        enabled=True,
        modified_date=datetime.now(timezone.utc),
        modified_by="user@example.com",
        secrets=secrets or ["c1"],
    )


def test_get_groups_list(mocker):
    app = create_app()
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch(
        "confidant.routes.groups.authnz.get_logged_in_user",
        return_value="user@example.com",
    )
    mocker.patch("confidant.routes.groups.acl_module_check", return_value=True)
    mocker.patch(
        "confidant.routes.groups.groupmanager.list_groups",
        return_value=GroupsResponse(groups=[_group(), _group("s2")]),
    )

    ret = app.test_client().get("/v1/groups")
    assert ret.status_code == 200
    assert [s["id"] for s in ret.get_json()["groups"]] == ["s1", "s2"]
    assert ret.get_json()["groups"][0]["tenant_id"] == "singletenant"


def test_get_group_detail(mocker):
    app = create_app()
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch(
        "confidant.routes.groups.authnz.get_logged_in_user",
        return_value="user@example.com",
    )
    mocker.patch("confidant.routes.groups.acl_module_check", return_value=True)
    mocker.patch(
        "confidant.routes.groups.groupmanager.get_group_latest",
        return_value=_group(),
    )

    ret = app.test_client().get("/v1/groups/s1")
    assert ret.status_code == 200
    body = ret.get_json()
    assert body["secrets"] == ["c1"]
    assert body["permissions"]["get"] is True


def test_get_group_versions_and_version_detail(mocker):
    app = create_app()
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch(
        "confidant.routes.groups.authnz.get_logged_in_user",
        return_value="user@example.com",
    )
    mocker.patch("confidant.routes.groups.acl_module_check", return_value=True)
    mocker.patch(
        "confidant.routes.groups.groupmanager.list_group_versions",
        return_value=RevisionsResponse(versions=[_group(), _group(revision=2)]),
    )
    mocker.patch(
        "confidant.routes.groups.groupmanager.get_group_version",
        return_value=_group(revision=2),
    )
    mocker.patch(
        "confidant.routes.groups.groupmanager.store.list_groups",
        return_value={"Items": []},
    )

    ret = app.test_client().get("/v1/groups/s1/versions")
    assert ret.status_code == 200
    assert [s["revision"] for s in ret.get_json()["versions"]] == [1, 2]

    ret = app.test_client().get("/v1/groups/s1/versions/2")
    assert ret.status_code == 200
    body = ret.get_json()
    assert body["revision"] == 2
    assert body["secrets"] == ["c1"]


def test_create_and_update_group(mocker):
    app = create_app()
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch(
        "confidant.routes.groups.authnz.get_logged_in_user",
        return_value="user@example.com",
    )
    mocker.patch("confidant.routes.groups.acl_module_check", return_value=True)
    mocker.patch(
        "confidant.routes.groups.groupmanager.get_group_latest",
        side_effect=[None, _group()],
    )
    mocker.patch(
        "confidant.routes.groups.groupmanager.create_group",
        return_value=(_group(), None),
    )
    mocker.patch(
        "confidant.routes.groups.groupmanager.update_group",
        return_value=(_group(revision=2), None),
    )
    mocker.patch(
        "confidant.routes.groups.secretmanager.get_secrets",
        return_value=[type("Cred", (), {"id": "c1"})()],
    )
    mocker.patch(
        "confidant.routes.groups.groupmanager.store.list_groups",
        return_value={"Items": []},
    )

    ret = app.test_client().put(
        "/v1/groups/s1",
        json={
            "secrets": ["c1"],
        },
    )
    assert ret.status_code == 200
    assert ret.get_json()["revision"] == 1
    assert ret.get_json()["secrets"] == ["c1"]

    ret = app.test_client().put(
        "/v1/groups/s1",
        json={
            "secrets": ["c1"],
        },
    )
    assert ret.status_code == 200
    assert ret.get_json()["revision"] == 2
    assert ret.get_json()["secrets"] == ["c1"]
