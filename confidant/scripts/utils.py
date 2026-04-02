import click
from confidant.utils.dynamodb import create_dynamodb_tables as create_tables


@click.command()
def create_dynamodb_tables():
    """
    Setup dynamo tables
    """
    create_tables()
