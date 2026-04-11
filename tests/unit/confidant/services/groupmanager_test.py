from confidant.services import groupmanager


def test_get_latest_group_revision():
    res = groupmanager.get_latest_group_revision("123", 1)
    assert res == 2


def test_group_grants_secret_action_matches_glob_path():
    group = {
        "policies": {
            "apps/*": ["decrypt"],
        }
    }

    assert (
        groupmanager.group_grants_secret_action(
            group,
            "apps/service-a",
            "decrypt",
        )
        is True
    )
    assert (
        groupmanager.group_grants_secret_action(
            group,
            "apps/service-a",
            "update",
        )
        is False
    )
