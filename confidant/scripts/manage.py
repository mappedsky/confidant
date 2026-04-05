import click
from flask.cli import FlaskGroup

from confidant.app import create_app
from confidant.scripts.archive import archive_secrets
from confidant.scripts.bootstrap import decrypt_secrets_bootstrap
from confidant.scripts.bootstrap import generate_secrets_bootstrap
from confidant.scripts.restore import restore_secrets
from confidant.scripts.utils import create_dynamodb_tables


def create_confidant_app():
    return create_app()


@click.group(cls=FlaskGroup, create_app=create_confidant_app)
def manager():
    """Management script for Confidant"""
    pass


manager.command("generate_secrets_bootstrap")(generate_secrets_bootstrap)
manager.command("decrypt_secrets_bootstrap")(decrypt_secrets_bootstrap)
manager.command("create_dynamodb_tables")(create_dynamodb_tables)
manager.command("archive_secrets")(archive_secrets)
manager.command("restore_secrets")(restore_secrets)


def main():
    manager()
