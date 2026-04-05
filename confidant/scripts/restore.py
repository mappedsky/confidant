import logging
import sys

import click
from pynamodb.exceptions import DoesNotExist

from confidant import settings
from confidant.models.secret import Secret
from confidant.models.secret import SecretArchive
from confidant.utils import stats

logger = logging.getLogger(__name__)

logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.INFO)


def _exit_with_error(message):
    logger.error(message)
    raise click.exceptions.Exit(1)


def secret_exists(secret_id):
    try:
        Secret.get(secret_id)
        return True
    except DoesNotExist:
        return False


def save_secrets(saves, force=False):
    # Do not restore a secret if it exists in the primary table.
    # We do this check at the point of all saves so that we can
    # restore revisions, if one of them failed to restore for some
    # reason.
    _saves = []
    for save in saves:
        if secret_exists(save.id):
            continue
        _saves.append(save)
    if not _saves:
        return
    save_msg = ", ".join([save.id for save in _saves])
    if not force:
        logger.info(
            "Would have restored secret and revisions: {}".format(
                save_msg,
            )
        )
        return
    logger.info(
        "Restoring secret and revisions: {}".format(
            save_msg,
        )
    )
    with Secret.batch_write() as batch:
        for save in _saves:
            batch.save(save)
    stats.incr("restore.save.success")


def restore_logic(archive_secrets, force):
    for archive_secret in archive_secrets:
        saves = []
        # restore the current record
        secret = Secret.from_archive_secret(
            archive_secret,
        )
        saves.append(secret)
        # fetch and restore every revision
        _range = range(1, secret.revision + 1)
        ids = []
        for i in _range:
            ids.append(f"{secret.id}-{i}")
        archive_revisions = SecretArchive.batch_get(ids)
        for archive_revision in archive_revisions:
            revision = Secret.from_archive_secret(
                archive_revision,
            )
            saves.append(revision)
        try:
            save_secrets(saves, force=force)
        except Exception:
            logger.exception(f"Failed to batch save {secret.id}.")
            stats.incr("restore.save.failure")
            continue


@click.command()
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help=(
        "By default, this script runs in dry-run mode, this option forces the "
        "run and makes the changes indicated by the dry run"
    ),
)
@click.option(
    "--ids",
    help=(
        "Restore a comma separated list of secret IDs. (mutually exclusive "
        "with --all)"
    ),
)
@click.option(
    "--all",
    "_all",
    is_flag=True,
    default=False,
    help=(
        "Restore all secrets from the permanent archive dynamodb table back "
        "into the primary store table."
    ),
)
def restore_secrets(force, ids, _all):
    """
    Command to restore secrets from the permanent archive dynamodb table
    back into the primary storage table.
    """
    if not settings.DYNAMODB_TABLE_ARCHIVE:
        _exit_with_error("DYNAMODB_TABLE_ARCHIVE is not configured, exiting.")
    if ids and _all:
        _exit_with_error("--ids and --all arguments are mutually exclusive")
    if not ids and not _all:
        _exit_with_error("Either --ids or --all argument must be provided")
    if ids:
        # filter strips an empty string
        _ids = [_id.strip() for _id in list(filter(None, ids.split(",")))]
        if not _ids:
            _exit_with_error("Passed in --ids argument is empty")
        secrets = SecretArchive.batch_get(_ids)
    else:
        secrets = SecretArchive.data_type_date_index.query(
            "secret",
        )
    restore_logic(secrets, force=force)
