from pytest_mock.plugin import MockerFixture

from confidant.app import create_app
from confidant.authnz import rbac


def test_default_acl(mocker: MockerFixture):
    mocker.patch("confidant.settings.USE_AUTH", True)
    app = create_app()
    with app.test_request_context("/fake"):
        g_mock = mocker.patch("confidant.authnz.g")

        g_mock.user_type = "user"
        assert rbac.default_acl(resource_type="group") is True

        g_mock.user_type = "service"
        g_mock.username = "test-service"
        assert (
            rbac.default_acl(
                resource_type="group",
                action="update",
                resource_id="test-service",
            )
            is False
        )

        g_mock.username = "bad-service"
        assert (
            rbac.default_acl(
                resource_type="group",
                action="metadata",
                resource_id="test-service",
            )
            is False
        )

        g_mock.username = "test-service"
        assert (
            rbac.default_acl(
                resource_type="group",
                action="metadata",
                resource_id="test-service",
            )
            is True
        )
        assert (
            rbac.default_acl(
                resource_type="group",
                action="get",
                resource_id="test-service",
            )
            is True
        )
        assert rbac.default_acl(resource_type="group", action="fake") is False

        g_mock.user_type = "badtype"
        assert rbac.default_acl(resource_type="group", action="get") is False


def test_no_acl():
    app = create_app()
    with app.test_request_context("/fake"):
        assert rbac.no_acl(resource_type="group", action="update") is True
