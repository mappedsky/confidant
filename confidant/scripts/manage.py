import click
from flask.cli import FlaskGroup

from confidant.app import create_app
from confidant.scripts.archive import archive_credentials
from confidant.scripts.utils import manage_kms_auth_grants
from confidant.scripts.utils import revoke_all_kms_auth_grants
from confidant.scripts.utils import create_dynamodb_tables
from confidant.scripts.bootstrap import generate_secrets_bootstrap
from confidant.scripts.bootstrap import decrypt_secrets_bootstrap
from confidant.scripts.migrate import (
    migrate_service_set_attribute,
)
from confidant.scripts.migrate_bool import migrate_boolean_attribute
from confidant.scripts.restore import restore_credentials


def create_confidant_app():
    return create_app()


@click.group(cls=FlaskGroup, create_app=create_confidant_app)
def manager():
    """Management script for Confidant"""
    pass


manager.command("manage_kms_auth_grants")(manage_kms_auth_grants)
manager.command("revoke_all_kms_auth_grants")(revoke_all_kms_auth_grants)
manager.command("generate_secrets_bootstrap")(generate_secrets_bootstrap)
manager.command("decrypt_secrets_bootstrap")(decrypt_secrets_bootstrap)
manager.command("create_dynamodb_tables")(create_dynamodb_tables)
manager.command("migrate_service_set_attribute")(migrate_service_set_attribute)
manager.command("migrate_boolean_attribute")(migrate_boolean_attribute)
manager.command("archive_credentials")(archive_credentials)
manager.command("restore_credentials")(restore_credentials)


def main():
    manager()
