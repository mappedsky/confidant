import click
from flask.cli import FlaskGroup

from confidant.app import create_app
from confidant.scripts.utils import create_dynamodb_tables


def create_confidant_app():
    return create_app()


@click.group(cls=FlaskGroup, create_app=create_confidant_app)
def manager():
    """Management script for Confidant"""
    pass


manager.command("create_dynamodb_tables")(create_dynamodb_tables)


def main():
    manager()
