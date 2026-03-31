import sys
import logging
from datetime import datetime
import click

from confidant import settings
from confidant.models.credential import Credential
from confidant.services import credentialmanager

logger = logging.getLogger(__name__)

logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.INFO)


def _exit_with_error(message):
    logger.error(message)
    raise click.exceptions.Exit(1)


@click.command()
@click.option('--days', type=int, help='Permanently archive disabled credentials last modified greater than this many days (mutually exclusive with --ids)')
@click.option('--force', is_flag=True, default=False, help='By default, this script runs in dry-run mode, this option forces the run and makes the changes indicated by the dry run')
@click.option('--ids', help='Archive a comma separated list of credential IDs. (mutually exclusive with --days)')
def archive_credentials(days, force, ids):
    """
    Command to permanently archive credentials to an archive dynamodb table.
    """
    if not settings.DYNAMODB_TABLE_ARCHIVE:
        _exit_with_error('DYNAMODB_TABLE_ARCHIVE is not configured, exiting.')
    if days and ids:
        _exit_with_error('--days and --ids options are mutually exclusive')
    if not days and not ids:
        _exit_with_error('Either --days or --ids options are required')
    credentials = []
    if ids:
        # filter strips an empty string
        _ids = [_id.strip() for _id in list(filter(None, ids.split(',')))]
        if not _ids:
            _exit_with_error('Passed in --ids argument is empty')
        for credential in Credential.batch_get(_ids):
            if credential.enabled:
                logger.warning(
                    'Skipping enabled credential {}'.format(credential.id)
                )
                continue
            credentials.append(credential)
    else:
        for credential in Credential.data_type_date_index.query(
            'credential'
        ):
            tz = credential.modified_date.tzinfo
            now = datetime.now(tz)
            delta = now - credential.modified_date
            if not credential.enabled and delta.days > days:
                credentials.append(credential)

    credentialmanager.archive_credentials(credentials, force=force)
