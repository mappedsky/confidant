from pytest_mock.plugin import MockerFixture

from confidant.services import groupmanager


def test_get_latest_group_revision(mocker: MockerFixture):
    mocker.patch("confidant.models.group.Group.get")
    res = groupmanager.get_latest_group_revision("123", 1)
    assert res == 2
