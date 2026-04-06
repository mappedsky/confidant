import copy
import logging
import sys

import click

from confidant import settings
from confidant.services.dynamodbstore import store
from confidant.utils import stats

logger = logging.getLogger(__name__)

logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.INFO)

_MULTI_TENANT_ERROR = "Restore maintenance scripts do not support MULTI_TENANT."


def _exit_with_error(message):
    logger.error(message)
    raise click.exceptions.Exit(1)


def _get_script_tenant_id():
    if settings.MULTI_TENANT:
        _exit_with_error(_MULTI_TENANT_ERROR)
    return "singletenant"


def secret_exists(tenant_id, secret_id):
    return store.get_secret_latest(tenant_id, secret_id) is not None


def _active_pk(tenant_id, secret_id):
    return f"TENANT#{tenant_id}#SECRET#{secret_id}"


def _restore_item_from_archive(item, tenant_id):
    restored = copy.deepcopy(item)
    restored["PK"] = _active_pk(tenant_id, item["id"])
    return restored


def _restore_list_item(secret, tenant_id):
    restored = {
        "PK": f"TENANT#{tenant_id}#SECRET_LIST",
        "SK": f"SECRET#{secret['id']}",
        "tenant_id": tenant_id,
        "id": secret["id"],
        "name": secret["name"],
        "revision": secret["revision"],
        "metadata": secret.get("metadata"),
        "modified_date": secret["modified_date"],
        "modified_by": secret["modified_by"],
        "documentation": secret.get("documentation"),
        "tags": secret.get("tags"),
        "last_decrypted_date": secret.get("last_decrypted_date"),
        "last_rotation_date": secret.get("last_rotation_date"),
        "secret_keys": secret.get("secret_keys"),
        "created_at": secret.get("created_at"),
        "updated_at": secret.get("updated_at"),
    }
    return restored


def _list_archived_secrets(tenant_id):
    page = None
    secrets = []
    while True:
        results = store.list_archive_secrets(
            tenant_id,
            last_evaluated_key=page,
        )
        secrets.extend(results.get("Items", []))
        page = results.get("LastEvaluatedKey")
        if not page:
            return secrets


def save_secrets(tenant_id, saves, force=False):
    _saves = []
    for save in saves:
        if secret_exists(tenant_id, save["id"]):
            continue
        _saves.append(save)
    if not _saves:
        return
    latest_ids = [save["id"] for save in _saves if save["SK"] == "#LATEST"]
    save_msg = ", ".join(latest_ids)
    if not force:
        logger.info(f"Would have restored secret and revisions: {save_msg}")
        return
    logger.info(f"Restoring secret and revisions: {save_msg}")
    store.batch_put_items(_saves)
    stats.incr("restore.save.success")


def restore_logic(tenant_id, archive_secrets, force):
    for archive_secret in archive_secrets:
        saves = []
        latest = _restore_item_from_archive(archive_secret, tenant_id)
        metadata = copy.deepcopy(latest)
        metadata["SK"] = "#METADATA"
        saves.append(metadata)
        saves.append(latest)
        archive_revisions = store.list_archive_secret_versions(
            tenant_id,
            archive_secret["id"],
        )
        for archive_revision in archive_revisions:
            revision = _restore_item_from_archive(archive_revision, tenant_id)
            saves.append(revision)
        saves.append(_restore_list_item(archive_secret, tenant_id))
        try:
            save_secrets(tenant_id, saves, force=force)
        except Exception:
            logger.exception(
                f"Failed to batch save restored secret {archive_secret['id']}."
            )
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
        "Restore all secrets from the archive partition in the primary "
        "dynamodb table back into the active secret partition."
    ),
)
def restore_secrets(force, ids, _all):
    """
    Command to restore secrets from the archive partition back into the
    primary storage partition.
    """
    if ids and _all:
        _exit_with_error("--ids and --all arguments are mutually exclusive")
    if not ids and not _all:
        _exit_with_error("Either --ids or --all argument must be provided")

    tenant_id = _get_script_tenant_id()
    if ids:
        _ids = [_id.strip() for _id in list(filter(None, ids.split(",")))]
        if not _ids:
            _exit_with_error("Passed in --ids argument is empty")
        secrets = []
        for secret_id in _ids:
            secret = store.get_archive_secret_latest(tenant_id, secret_id)
            if secret is None:
                logger.warning(f"Skipping missing archived secret {secret_id}")
                continue
            secrets.append(secret)
    else:
        secrets = _list_archived_secrets(tenant_id)
    restore_logic(tenant_id, secrets, force=force)
