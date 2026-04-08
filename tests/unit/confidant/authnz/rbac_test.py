from pytest_mock.plugin import MockerFixture

from confidant.app import create_app
from confidant.authnz import rbac


def test_default_acl_allows_builtin_admin(mocker: MockerFixture):
    mocker.patch("confidant.settings.USE_AUTH", True)
    app = create_app()
    with app.test_request_context("/fake"):
        g_mock = mocker.patch("confidant.authnz.g")
        g_mock.current_principal = None
        mocker.patch(
            "confidant.authnz.get_logged_in_group_ids",
            return_value=["confidant-administrator"],
        )

        assert rbac.default_acl(resource_type="secret", action="delete") is True
        assert rbac.default_acl(resource_type="group", action="update") is True


def test_default_acl_allows_group_admin_group_actions(mocker: MockerFixture):
    mocker.patch("confidant.settings.USE_AUTH", True)
    app = create_app()
    with app.test_request_context("/fake"):
        mocker.patch(
            "confidant.authnz.get_logged_in_group_ids",
            return_value=["confidant-group-administrator"],
        )

        assert rbac.default_acl(resource_type="group", action="list") is True
        assert rbac.default_acl(resource_type="group", action="get") is True
        grp_meta = rbac.default_acl(resource_type="group", action="metadata")
        assert grp_meta is True
        assert rbac.default_acl(resource_type="group", action="create") is True
        assert rbac.default_acl(resource_type="group", action="update") is True
        assert rbac.default_acl(resource_type="group", action="delete") is True
        assert rbac.default_acl(resource_type="secret", action="list") is False
        sec_create = rbac.default_acl(resource_type="secret", action="create")
        assert sec_create is False


def test_default_acl_allows_auditor_metadata_and_lists(mocker: MockerFixture):
    mocker.patch("confidant.settings.USE_AUTH", True)
    app = create_app()
    with app.test_request_context("/fake"):
        mocker.patch(
            "confidant.authnz.get_logged_in_group_ids",
            return_value=["confidant-auditor"],
        )
        mocker.patch(
            "confidant.authnz.rbac.groupmanager.get_groups_by_ids",
            return_value=[],
        )

        assert rbac.default_acl(resource_type="secret", action="list") is True
        assert rbac.default_acl(resource_type="group", action="list") is True
        sec_meta = rbac.default_acl(resource_type="secret", action="metadata")
        assert sec_meta is True
        grp_meta = rbac.default_acl(resource_type="group", action="metadata")
        assert grp_meta is True
        assert rbac.default_acl(resource_type="group", action="get") is True
        sec_dec = rbac.default_acl(resource_type="secret", action="decrypt")
        assert sec_dec is False


def test_default_acl_falls_back_to_secret_policies(mocker: MockerFixture):
    mocker.patch("confidant.settings.USE_AUTH", True)
    app = create_app()
    with app.test_request_context("/fake"):
        mocker.patch(
            "confidant.authnz.get_logged_in_group_ids",
            return_value=["policy-group"],
        )
        mocker.patch(
            "confidant.authnz.get_tenant_id",
            return_value="singletenant",
        )
        group_mock = mocker.patch(
            "confidant.authnz.rbac.groupmanager.get_groups_by_ids",
            return_value=[
                {
                    "policies": {
                        "*": ["list"],
                        "apps/*": ["decrypt", "create"],
                    }
                }
            ],
        )

        assert (
            rbac.default_acl(
                resource_type="secret",
                action="list",
                resource_id="*",
            )
            is True
        )
        assert (
            rbac.default_acl(
                resource_type="secret",
                action="decrypt",
                resource_id="apps/service-a",
            )
            is True
        )
        assert (
            rbac.default_acl(
                resource_type="secret",
                action="create",
                resource_id="apps/service-a",
            )
            is True
        )
        assert (
            rbac.default_acl(
                resource_type="secret",
                action="delete",
                resource_id="apps/service-a",
            )
            is False
        )
        group_mock.assert_called()


def test_default_acl_denies_unknown_access(mocker: MockerFixture):
    mocker.patch("confidant.settings.USE_AUTH", True)
    app = create_app()
    with app.test_request_context("/fake"):
        mocker.patch(
            "confidant.authnz.get_logged_in_group_ids",
            return_value=[],
        )

        sec_dec = rbac.default_acl(resource_type="secret", action="decrypt")
        assert sec_dec is False
        assert rbac.default_acl(resource_type="group", action="create") is False


def test_no_acl():
    app = create_app()
    with app.test_request_context("/fake"):
        assert rbac.no_acl(resource_type="group", action="update") is True
