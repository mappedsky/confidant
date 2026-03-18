import sys
import logging
import click
from pynamodb.exceptions import DoesNotExist

from confidant import settings
from confidant.models.credential import Credential, CredentialArchive
from confidant.utils import stats

logger = logging.getLogger(__name__)

logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.INFO)


def credential_exists(credential_id):
    try:
        Credential.get(credential_id)
        return True
    except DoesNotExist:
        return False


def save_credentials(saves, force=False):
    # Do not restore a credential if it exists in the primary table.
    # We do this check at the point of all saves so that we can
    # restore revisions, if one of them failed to restore for some
    # reason.
    _saves = []
    for save in saves:
        if credential_exists(save.id):
            continue
        _saves.append(save)
    if not _saves:
        return
    save_msg = ', '.join([save.id for save in _saves])
    if not force:
        logger.info(
            'Would have restored credential and revisions: {}'.format(
                save_msg,
            )
        )
        return
    logger.info(
        'Restoring credential and revisions: {}'.format(
            save_msg,
        )
    )
    with Credential.batch_write() as batch:
        for save in _saves:
            batch.save(save)
    stats.incr('restore.save.success')


def restore_logic(archive_credentials, force):
    for archive_credential in archive_credentials:
        saves = []
        # restore the current record
        credential = Credential.from_archive_credential(
            archive_credential,
        )
        saves.append(credential)
        # fetch and restore every revision
        _range = range(1, credential.revision + 1)
        ids = []
        for i in _range:
            ids.append("{0}-{1}".format(credential.id, i))
        archive_revisions = CredentialArchive.batch_get(ids)
        for archive_revision in archive_revisions:
            revision = Credential.from_archive_credential(
                archive_revision,
            )
            saves.append(revision)
        try:
            save_credentials(saves, force=force)
        except Exception:
            logger.exception(
                'Failed to batch save {}.'.format(
                    credential.id
                )
            )
            stats.incr('restore.save.failure')
            continue


@click.command()
@click.option('--force', is_flag=True, default=False, help='By default, this script runs in dry-run mode, this option forces the run and makes the changes indicated by the dry run')
@click.option('--ids', help='Restore a comma separated list of credential IDs. (mutually exclusive with --all)')
@click.option('--all', '_all', is_flag=True, default=False, help='Restore all credentials from the permanent archive dynamodb table back into the primary store table.')
def restore_credentials(force, ids, _all):
    """
    Command to restore credentials from the permanent archive dynamodb table
    back into the primary storage table.
    """
    if not settings.DYNAMODB_TABLE_ARCHIVE:
        logger.error('DYNAMODB_TABLE_ARCHIVE is not configured, exiting.')
        return 1
    if ids and _all:
        logger.error('--ids and --all arguments are mutually exclusive')
        return 1
    if not ids and not _all:
        logger.error('Either --ids or --all argument must be provided')
        return 1
    if ids:
        # filter strips an empty string
        _ids = [_id.strip() for _id in list(filter(None, ids.split(',')))]
        if not _ids:
            logger.error('Passed in --ids argument is empty')
            return 1
        credentials = CredentialArchive.batch_get(_ids)
    else:
        credentials = CredentialArchive.data_type_date_index.query(
            'credential',
        )
    restore_logic(credentials, force=force)
