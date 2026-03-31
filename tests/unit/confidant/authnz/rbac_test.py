from pytest_mock.plugin import MockerFixture

from confidant.app import create_app
from confidant.authnz import rbac


def test_default_acl(mocker: MockerFixture):
    mocker.patch('confidant.settings.USE_AUTH', True)
    app = create_app()
    with app.test_request_context('/fake'):
        g_mock = mocker.patch('confidant.authnz.g')

        # Test for user type is user
        g_mock.user_type = 'user'
        assert rbac.default_acl(resource_type='service') is True
        # Test for user type is service, but not an allowed resource type
        g_mock.user_type = 'service'
        g_mock.username = 'test-service'
        assert rbac.default_acl(
            resource_type='service',
            action='update',
            resource_id='test-service'
        ) is False
        # Test for user type is service, and an allowed resource, with metadata
        # action, but service name doesn't match
        g_mock.username = 'bad-service'
        assert rbac.default_acl(
            resource_type='service',
            action='metadata',
            resource_id='test-service',
        ) is False
        # Test for user type is service, and an allowed resource, with metadata
        # action
        g_mock.username = 'test-service'
        assert rbac.default_acl(
            resource_type='service',
            action='metadata',
            resource_id='test-service',
        ) is True
        # Test for user type is service, and an allowed resource, with get
        # action
        assert rbac.default_acl(
            resource_type='service',
            action='get',
            resource_id='test-service',
        ) is True
        # Test for user type is service, and an allowed resource, with
        # disallowed fake action
        assert rbac.default_acl(resource_type='service', action='fake') is False
        # Test for bad user type
        g_mock.user_type = 'badtype'
        assert rbac.default_acl(resource_type='service', action='get') is False


def test_no_acl():
    app = create_app()
    with app.test_request_context('/fake'):
        assert rbac.no_acl(resource_type='service', action='update') is True
