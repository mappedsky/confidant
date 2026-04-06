from confidant.services import groupmanager


def test_get_latest_group_revision():
    res = groupmanager.get_latest_group_revision("123", 1)
    assert res == 2
