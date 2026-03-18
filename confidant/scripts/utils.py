import sys
import logging
import click
from botocore.exceptions import ClientError

import confidant.clients
from confidant import settings
from confidant.services import keymanager
from confidant.models.service import Service
from confidant.utils.dynamodb import create_dynamodb_tables

logger = logging.getLogger(__name__)

logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.INFO)


@click.command()
def manage_kms_auth_grants():
    """
    Ensure KMS grants are setup for services
    """
    iam_resource = confidant.clients.get_boto_resource('iam')

    grants = keymanager.get_grants()
    try:
        roles = [x for x in iam_resource.roles.all()]
    except ClientError:
        logger.error('Failed to fetch IAM roles.')
        return
    services = []
    for service in Service.data_type_date_index.query('service'):
        services.append(service.id)
    for role in roles:
        if role.name in services:
            logger.info('Managing grants for {0}.'.format(role.name))
            keymanager._ensure_grants(role, grants)
    logger.info('Finished managing grants.')


@click.command()
def revoke_all_kms_auth_grants():
    """
    Revoke all KMS grants
    """
    kms_client = confidant.clients.get_boto_client(
        'kms',
        settings.KMS_URL,
    )
    grants = keymanager.get_grants()
    for grant in grants:
        kms_client.revoke_grant(
            KeyId=keymanager.get_key_id(settings.AUTH_KEY),
            GrantId=grant['GrantId']
        )
    logger.info('Finished revoking grants.')


@click.command()
def create_dynamodb_tables():
    """
    Setup dynamo tables
    """
    create_dynamodb_tables()
