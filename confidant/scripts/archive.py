import copy
import logging
import sys
from datetime import datetime
from datetime import timezone

import click

from confidant import settings
from confidant.services.dynamodbstore import store

logger = logging.getLogger(__name__)

logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.INFO)

_MULTI_TENANT_ERROR = "Archive maintenance scripts do not support MULTI_TENANT."
_DEPENDENCY_WARNING = "".join(
    (
        "Skipping archive for a secret ",
        "that is still mapped to groups.",
    )
)
_ALREADY_ARCHIVED_WARNING = "".join(
    (
        "Skipping archive for a secret ",
        "that is already archived.",
    )
)


def _exit_with_error(message):
    logger.error(message)
    raise click.exceptions.Exit(1)


def _get_script_tenant_id():
    if settings.MULTI_TENANT:
        _exit_with_error(_MULTI_TENANT_ERROR)
    return "singletenant"


def _archive_pk(tenant_id, secret_id):
    return f"TENANT#{tenant_id}#ARCHIVE_SECRET#{secret_id}"


def _archive_item_from_secret(item, tenant_id):
    archived = copy.deepcopy(item)
    archived["PK"] = _archive_pk(tenant_id, item["id"])
    return archived


def _list_candidate_secrets(tenant_id, days):
    page = None
    secrets = []
    while True:
        results = store.list_secrets(
            tenant_id,
            last_evaluated_key=page,
        )
        for secret in results.get("Items", []):
            modified_date = datetime.fromisoformat(secret["modified_date"])
            now = datetime.now(timezone.utc)
            delta = now - modified_date
            if delta.days > days:
                secrets.append(secret)
        page = results.get("LastEvaluatedKey")
        if not page:
            return secrets


def _archive_secret(tenant_id, secret, force=False):
    dependencies = store.list_groups_for_secret(tenant_id, secret["id"])
    if dependencies:
        logger.warning(_DEPENDENCY_WARNING)
        return
    if store.get_archive_secret_latest(tenant_id, secret["id"]):
        logger.warning(_ALREADY_ARCHIVED_WARNING)
        return

    versions = store.list_secret_versions(tenant_id, secret["id"])
    archived_items = [_archive_item_from_secret(secret, tenant_id)]
    archived_items.extend(
        _archive_item_from_secret(version, tenant_id) for version in versions
    )
    if not force:
        logger.info("Would archive one secret and its revisions.")
        return

    logger.info("Archiving one secret and its revisions.")
    store.put_archive_secret(tenant_id, secret["id"], archived_items)
    store.delete_secret(tenant_id, secret["id"])


@click.command()
@click.option(
    "--days",
    type=int,
    help=(
        "Permanently archive secrets last modified greater than this "
        "many days (mutually exclusive with --ids)"
    ),
)
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
        "Archive a comma separated list of secret IDs. (mutually exclusive "
        "with --days)"
    ),
)
def archive_secrets(days, force, ids):
    """
    Command to permanently archive secrets inside the primary dynamodb table.
    """
    if days and ids:
        _exit_with_error("--days and --ids options are mutually exclusive")
    if not days and not ids:
        _exit_with_error("Either --days or --ids options are required")

    tenant_id = _get_script_tenant_id()
    secrets = []
    if ids:
        _ids = [_id.strip() for _id in list(filter(None, ids.split(",")))]
        if not _ids:
            _exit_with_error("Passed in --ids argument is empty")
        for secret_id in _ids:
            secret = store.get_secret_latest(tenant_id, secret_id)
            if secret is None:
                continue
            secrets.append(secret)
    else:
        secrets = _list_candidate_secrets(tenant_id, days)

    for secret in secrets:
        _archive_secret(tenant_id, secret, force=force)
