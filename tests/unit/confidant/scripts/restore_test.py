from click.testing import CliRunner
from pytest_mock.plugin import MockerFixture

from confidant.scripts.restore import restore_logic
from confidant.scripts.restore import restore_secrets
from confidant.scripts.restore import save_secrets


def _archive_secret(secret_id="1234"):
    return {
        "PK": f"TENANT#singletenant#ARCHIVE_SECRET#{secret_id}",
        "SK": "#LATEST",
        "tenant_id": "singletenant",
        "id": secret_id,
        "name": "test",
        "revision": 2,
        "modified_date": "2026-04-01T05:15:55+00:00",
        "modified_by": "test@example.com",
        "secret_keys": ["foo"],
    }


def _archive_revision(secret_id, revision):
    return {
        "PK": f"TENANT#singletenant#ARCHIVE_SECRET#{secret_id}",
        "SK": f"VERSION#{revision:010d}",
        "tenant_id": "singletenant",
        "id": secret_id,
        "name": "test",
        "revision": revision,
        "modified_date": "2026-04-01T05:15:55+00:00",
        "modified_by": "test@example.com",
        "secret_keys": ["foo"],
    }


def test_save_skips_existing_secret(mocker: MockerFixture):
    batch_put = mocker.patch("confidant.scripts.restore.store.batch_put_items")
    saves = [
        {
            "PK": "TENANT#singletenant#SECRET#1234",
            "SK": "#LATEST",
            "id": "1234",
        }
    ]
    mocker.patch(
        "confidant.scripts.restore.secret_exists",
        return_value=True,
    )

    save_secrets("singletenant", saves, force=True)

    batch_put.assert_not_called()


def test_save_dry_run_does_not_write(mocker: MockerFixture):
    batch_put = mocker.patch("confidant.scripts.restore.store.batch_put_items")
    saves = [
        {
            "PK": "TENANT#singletenant#SECRET#1234",
            "SK": "#LATEST",
            "id": "1234",
        }
    ]
    mocker.patch(
        "confidant.scripts.restore.secret_exists",
        return_value=False,
    )

    save_secrets("singletenant", saves, force=False)

    batch_put.assert_not_called()


def test_save_writes_when_forced(mocker: MockerFixture):
    batch_put = mocker.patch("confidant.scripts.restore.store.batch_put_items")
    saves = [
        {
            "PK": "TENANT#singletenant#SECRET#1234",
            "SK": "#LATEST",
            "id": "1234",
        }
    ]
    mocker.patch(
        "confidant.scripts.restore.secret_exists",
        return_value=False,
    )

    save_secrets("singletenant", saves, force=True)

    batch_put.assert_called_once_with(saves)


def test_restore_logic(
    mocker: MockerFixture,
):
    archive_secret = _archive_secret()
    archive_revisions = [
        _archive_revision("1234", 1),
        _archive_revision("1234", 2),
    ]
    save_mock = mocker.patch("confidant.scripts.restore.save_secrets")
    mocker.patch(
        "confidant.scripts.restore.store.list_archive_secret_versions",
        return_value=archive_revisions,
    )

    restore_logic("singletenant", [archive_secret], force=True)

    save_mock.assert_called_once()
    saves = save_mock.call_args.args[1]
    assert [item["SK"] for item in saves] == [
        "#METADATA",
        "#LATEST",
        "VERSION#0000000001",
        "VERSION#0000000002",
        "SECRET#1234",
    ]


def test_run_bad_args():
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
):
    archive_secret = _archive_secret()
    restore_mock = mocker.patch("confidant.scripts.restore.restore_logic")
    mocker.patch(
        "confidant.scripts.restore.store.list_archive_secrets",
        return_value={"Items": [archive_secret]},
    )

    runner = CliRunner()
    runner.invoke(restore_secrets, ["--all", "--force"])

    restore_mock.assert_called_once_with(
        "singletenant",
        [archive_secret],
        force=True,
    )


def test_run_ids(
    mocker: MockerFixture,
):
    archive_secret = _archive_secret()
    restore_mock = mocker.patch("confidant.scripts.restore.restore_logic")
    mocker.patch(
        "confidant.scripts.restore.store.get_archive_secret_latest",
        return_value=archive_secret,
    )

    runner = CliRunner()
    runner.invoke(restore_secrets, ["--ids", "1234", "--force"])

    restore_mock.assert_called_once_with(
        "singletenant",
        [archive_secret],
        force=True,
    )


def test_run_ids_skips_missing_archive_secret(
    mocker: MockerFixture,
):
    restore_mock = mocker.patch("confidant.scripts.restore.restore_logic")
    mocker.patch(
        "confidant.scripts.restore.store.get_archive_secret_latest",
        return_value=None,
    )

    runner = CliRunner()
    runner.invoke(restore_secrets, ["--ids", "1234", "--force"])

    restore_mock.assert_called_once_with("singletenant", [], force=True)


def test_restore_logic_handles_save_failures(mocker: MockerFixture):
    archive_secret = _archive_secret()
    mocker.patch(
        "confidant.scripts.restore.store.list_archive_secret_versions",
        return_value=[],
    )
    save_mock = mocker.patch(
        "confidant.scripts.restore.save_secrets",
        side_effect=RuntimeError("boom"),
    )
    incr_mock = mocker.patch("confidant.scripts.restore.stats.incr")

    restore_logic("singletenant", [archive_secret], force=True)

    save_mock.assert_called_once()
    incr_mock.assert_called_with("restore.save.failure")
