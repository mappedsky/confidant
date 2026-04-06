from click.testing import CliRunner
from pytest_mock.plugin import MockerFixture

from confidant.scripts.archive import _archive_secret
from confidant.scripts.archive import archive_secrets

_PUT_ARCHIVE_SECRET = "confidant.scripts.archive.store.put_archive_secret"
_DELETE_SECRET = "confidant.scripts.archive.store.delete_secret"


def _secret(secret_id="1234"):
    return {
        "PK": f"TENANT#singletenant#SECRET#{secret_id}",
        "SK": "#LATEST",
        "tenant_id": "singletenant",
        "id": secret_id,
        "name": "test",
        "revision": 2,
        "modified_date": "2026-04-01T05:15:55+00:00",
        "modified_by": "test@example.com",
        "secret_keys": ["foo"],
    }


def _revision(secret_id, revision):
    return {
        "PK": f"TENANT#singletenant#SECRET#{secret_id}",
        "SK": f"VERSION#{revision:010d}",
        "tenant_id": "singletenant",
        "id": secret_id,
        "name": "test",
        "revision": revision,
        "modified_date": "2026-04-01T05:15:55+00:00",
        "modified_by": "test@example.com",
        "secret_keys": ["foo"],
    }


def test_archive_secret_skips_mapped_secret(mocker: MockerFixture):
    put_mock = mocker.patch(_PUT_ARCHIVE_SECRET)
    delete_mock = mocker.patch(_DELETE_SECRET)
    mocker.patch(
        "confidant.scripts.archive.store.list_groups_for_secret",
        return_value=[{"id": "group-a"}],
    )

    _archive_secret("singletenant", _secret(), force=True)

    put_mock.assert_not_called()
    delete_mock.assert_not_called()


def test_archive_secret_writes_archive_and_deletes_active(
    mocker: MockerFixture,
):
    secret = _secret()
    put_mock = mocker.patch(_PUT_ARCHIVE_SECRET)
    delete_mock = mocker.patch(_DELETE_SECRET)
    mocker.patch(
        "confidant.scripts.archive.store.list_groups_for_secret",
        return_value=[],
    )
    mocker.patch(
        "confidant.scripts.archive.store.get_archive_secret_latest",
        return_value=None,
    )
    mocker.patch(
        "confidant.scripts.archive.store.list_secret_versions",
        return_value=[_revision("1234", 1), _revision("1234", 2)],
    )

    _archive_secret("singletenant", secret, force=True)

    put_mock.assert_called_once()
    delete_mock.assert_called_once_with("singletenant", "1234")
    archived_items = put_mock.call_args.args[2]
    assert archived_items[0]["PK"] == "TENANT#singletenant#ARCHIVE_SECRET#1234"


def test_archive_secret_dry_run_does_not_write(mocker: MockerFixture):
    put_mock = mocker.patch(_PUT_ARCHIVE_SECRET)
    delete_mock = mocker.patch(_DELETE_SECRET)
    mocker.patch(
        "confidant.scripts.archive.store.list_groups_for_secret",
        return_value=[],
    )
    mocker.patch(
        "confidant.scripts.archive.store.get_archive_secret_latest",
        return_value=None,
    )
    mocker.patch(
        "confidant.scripts.archive.store.list_secret_versions",
        return_value=[],
    )

    _archive_secret("singletenant", _secret(), force=False)

    put_mock.assert_not_called()
    delete_mock.assert_not_called()


def test_run_bad_args():
    runner = CliRunner()
    result = runner.invoke(archive_secrets, ["--force"])
    assert result.exit_code == 1
    result = runner.invoke(
        archive_secrets,
        ["--days", "5", "--ids", "1234", "--force"],
    )
    assert result.exit_code == 1


def test_run_ids(mocker: MockerFixture):
    archive_mock = mocker.patch("confidant.scripts.archive._archive_secret")
    mocker.patch(
        "confidant.scripts.archive.store.get_secret_latest",
        return_value=_secret(),
    )

    runner = CliRunner()
    runner.invoke(archive_secrets, ["--ids", "1234", "--force"])

    archive_mock.assert_called_once_with(
        "singletenant",
        _secret(),
        force=True,
    )


def test_run_days(mocker: MockerFixture):
    archive_mock = mocker.patch("confidant.scripts.archive._archive_secret")
    mocker.patch(
        "confidant.scripts.archive._list_candidate_secrets",
        return_value=[_secret()],
    )

    runner = CliRunner()
    runner.invoke(archive_secrets, ["--days", "5", "--force"])

    archive_mock.assert_called_once_with(
        "singletenant",
        _secret(),
        force=True,
    )
