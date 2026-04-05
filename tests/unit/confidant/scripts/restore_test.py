from datetime import datetime
from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner
from pytest_mock.plugin import MockerFixture

from confidant.models.secret import Secret
from confidant.models.secret import SecretArchive
from confidant.scripts.restore import restore_logic
from confidant.scripts.restore import restore_secrets
from confidant.scripts.restore import save_secrets


@pytest.fixture
def now() -> datetime:
    return datetime.now()


@pytest.fixture
def old_date() -> datetime:
    return datetime.now() - timedelta(30)


@pytest.fixture()
def save_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("confidant.scripts.restore.save_secrets")


@pytest.fixture()
def restore_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("confidant.scripts.restore.restore_logic")


@pytest.fixture
def secrets(mocker: MockerFixture, now: datetime) -> dict[str, list[Secret]]:
    archive_secret = SecretArchive(
        id="1234",
        name="test",
        data_type="secret",
        revision=2,
        enabled=True,
        modified_date=now,
        modified_by="test@example.com",
    )
    secret = Secret.from_archive_secret(archive_secret)
    archive_revision1 = SecretArchive(
        id="1234-1",
        name="test revision1",
        data_type="archive-secret",
        revision=1,
        enabled=True,
        modified_date=now,
        modified_by="test@example.com",
    )
    revision1 = Secret.from_archive_secret(archive_revision1)
    archive_revision2 = Secret(
        id="1234-2",
        name="test revision2",
        data_type="archive-secret",
        revision=2,
        enabled=True,
        modified_date=now,
        modified_by="test@example.com",
    )
    revision2 = Secret.from_archive_secret(archive_revision2)

    def from_archive_secret(archive_secret: SecretArchive):
        if archive_secret.id == "1234":
            return secret
        elif archive_secret.id == "1234-1":
            return revision1
        elif archive_secret.id == "1234-2":
            return revision2

    mocker.patch.object(Secret, "from_archive_secret", from_archive_secret)
    return {
        "secrets": [secret],
        "archive_secrets": [archive_secret],
        "revisions": [revision1, revision2],
        "archive_revisions": [archive_revision1, archive_revision2],
    }


@pytest.fixture
def old_disabled_secrets(
    secrets: dict[str, list[Secret]], old_date: datetime
) -> dict[str, list[Secret]]:
    for secret in secrets["secrets"]:
        secret.modified_date = old_date
        secret.enabled = False
    for secret in secrets["archive_secrets"]:
        secret.modified_date = old_date
        secret.enabled = False
    for revision in secrets["revisions"]:
        revision.modified_date = old_date
        revision.enabled = False
    for revision in secrets["archive_revisions"]:
        revision.modified_date = old_date
        revision.enabled = False
    return secrets


def test_save(mocker: MockerFixture, secrets: dict[str, list[Secret]]):
    save_mock = mocker.patch("pynamodb.models.BatchWrite.save")
    mocker.patch("pynamodb.models.BatchWrite.commit")
    mocker.patch(
        "confidant.scripts.restore.secret_exists",
        return_value=True,
    )
    save_secrets(secrets["secrets"], force=True)
    assert save_mock.called is False

    mocker.patch(
        "confidant.scripts.restore.secret_exists",
        return_value=False,
    )
    save_secrets(secrets["secrets"], force=False)
    assert save_mock.called is False

    save_secrets(secrets["secrets"], force=True)
    assert save_mock.called is True


def test_restore_secrets(
    mocker: MockerFixture,
    old_disabled_secrets: dict[str, list[Secret]],
    save_mock: MagicMock,
):
    mocker.patch(
        "confidant.scripts.restore.SecretArchive.batch_get",
        return_value=old_disabled_secrets["archive_revisions"],
    )
    restore_logic(old_disabled_secrets["archive_secrets"], force=True)

    save_mock.assert_called_with(
        old_disabled_secrets["secrets"]
        + old_disabled_secrets["revisions"],  # noqa:E501
        force=True,
    )


def test_restore_old_disabled_unmapped_secret_no_force(
    mocker: MockerFixture,
    old_disabled_secrets: dict[str, list[Secret]],
    save_mock: MagicMock,
):
    mocker.patch(
        "confidant.scripts.restore.SecretArchive.batch_get",
        return_value=old_disabled_secrets["archive_revisions"],
    )
    restore_logic(old_disabled_secrets["archive_secrets"], force=False)

    save_mock.assert_called_with(
        old_disabled_secrets["secrets"]
        + old_disabled_secrets["revisions"],  # noqa:E501
        force=False,
    )


def test_run_no_archive_table(mocker: MockerFixture):
    mocker.patch(
        "confidant.scripts.restore.settings.DYNAMODB_TABLE_ARCHIVE",
        None,
    )
    runner = CliRunner()
    result = runner.invoke(restore_secrets, ["--all", "--force"])
    assert result.exit_code == 1


def test_run_bad_args(mocker: MockerFixture):
    runner = CliRunner()
    result = runner.invoke(restore_secrets, ["--force"])
    assert result.exit_code == 1
    result = runner.invoke(
        restore_secrets,
        ["--all", "--ids", "1234", "--force"],
    )
    assert result.exit_code == 1


def test_run_all(
    mocker: MockerFixture,
    secrets: dict[str, list[Secret]],
    restore_mock: MagicMock,
):
    mocker.patch(
        "confidant.scripts.restore.SecretArchive.data_type_date_index.query",
        return_value=secrets["archive_secrets"],
    )
    runner = CliRunner()
    runner.invoke(restore_secrets, ["--all", "--force"])
    restore_mock.assert_called_with(
        secrets["archive_secrets"],
        force=True,
    )


def test_run_ids(
    mocker: MockerFixture,
    secrets: dict[str, list[Secret]],
    restore_mock: MagicMock,
):
    mocker.patch(
        "confidant.scripts.restore.SecretArchive.batch_get",
        return_value=secrets["archive_secrets"],
    )
    cred_ids = [cred.id for cred in secrets["archive_secrets"]]
    ids = ",".join(cred_ids)
    runner = CliRunner()
    runner.invoke(restore_secrets, ["--ids", ids, "--force"])

    restore_mock.assert_called_with(
        secrets["archive_secrets"],
        force=True,
    )
