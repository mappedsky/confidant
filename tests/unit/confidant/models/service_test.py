from datetime import datetime
from pytest_mock.plugin import MockerFixture

from confidant.models.service import Service


def test_equals(mocker: MockerFixture):
    service1 = Service(
        id='test',
        credentials=['abc', 'def'],
    )
    service2 = Service(
        id='test',
        credentials=['abc', 'def'],
    )
    assert service1.equals(service2) is True


def test_not_equals(mocker: MockerFixture):
    service1 = Service(
        id='test',
        credentials=['abc', 'def'],
    )
    service2 = Service(
        id='test',
        credentials=['def'],
    )
    assert service1.equals(service2) is False


def test_diff(mocker: MockerFixture):
    modified_by = 'test@example.com'
    modified_date_old = datetime.now
    modified_date_new = datetime.now
    old = Service(
        id='test',
        revision=1,
        credentials=['abc', 'def'],
        modified_by=modified_by,
        modified_date=modified_date_old,
    )
    new = Service(
        id='test',
        revision=1,
        credentials=['def'],
        modified_by=modified_by,
        modified_date=modified_date_new,
    )
    # If the revisions are the same we short-circuit, so even if the contents
    # differ, there should be no diff.
    assert old.diff(new) == {}

    new.revision = 2
    expected_diff = {
        'credentials': {
            'removed': ['abc'],
        },
        'modified_by': {
            'removed': 'test@example.com',
            'added': 'test@example.com',
        },
        'modified_date': {
            'removed': modified_date_old,
            'added': modified_date_new,
        },
    }

    assert old.diff(new) == expected_diff
