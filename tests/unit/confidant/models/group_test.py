from datetime import datetime

from pytest_mock.plugin import MockerFixture

from confidant.models.group import Group


def test_equals(mocker: MockerFixture):
    group1 = Group(
        id="test",
        secrets=["abc", "def"],
    )
    group2 = Group(
        id="test",
        secrets=["abc", "def"],
    )
    assert group1.equals(group2) is True


def test_not_equals(mocker: MockerFixture):
    group1 = Group(
        id="test",
        secrets=["abc", "def"],
    )
    group2 = Group(
        id="test",
        secrets=["def"],
    )
    assert group1.equals(group2) is False


def test_diff(mocker: MockerFixture):
    modified_by = "test@example.com"
    modified_date_old = datetime.now
    modified_date_new = datetime.now
    old = Group(
        id="test",
        revision=1,
        secrets=["abc", "def"],
        modified_by=modified_by,
        modified_date=modified_date_old,
    )
    new = Group(
        id="test",
        revision=1,
        secrets=["def"],
        modified_by=modified_by,
        modified_date=modified_date_new,
    )
    # If the revisions are the same we short-circuit, so even if the contents
    # differ, there should be no diff.
    assert old.diff(new) == {}

    new.revision = 2
    expected_diff = {
        "secrets": {
            "removed": ["abc"],
        },
        "modified_by": {
            "removed": "test@example.com",
            "added": "test@example.com",
        },
        "modified_date": {
            "removed": modified_date_old,
            "added": modified_date_new,
        },
    }

    assert old.diff(new) == expected_diff
