import json
import logging
from os import getenv

from confidant.encrypted_settings import EncryptedSettings

logger = logging.getLogger(__name__)


class SettingsError(Exception):
    pass


def bool_env(var_name, default=False):
    """
    Get an environment variable coerced to a boolean value.

    Example:
        Bash:
            $ export SOME_VAL=True
        settings.py:
            SOME_VAL = bool_env('SOME_VAL', False)

    Arguments:
        var_name: The name of the environment variable.
        default: The default to use if `var_name` is not specified in the
            environment.

    Returns:
        `var_name` or `default` coerced to a boolean using the following
        rules:
        "False", "false" or "" => False
        Any other non-empty string => True
    """
    test_val = getenv(var_name, default)
    # Explicitly check for 'False', 'false', and '0' since all non-empty
    # string are normally coerced to True.
    if test_val in ("False", "false", "0"):
        return False
    return bool(test_val)


def float_env(var_name, default=0.0):
    """
    Get an environment variable coerced to a float value.
    This has the same arguments as bool_env. If a value cannot be coerced to a
    float, a ValueError will be raised.
    """
    return float(getenv(var_name, default))


def int_env(var_name, default=0):
    """
    Get an environment variable coerced to an integer value.
    This has the same arguments as bool_env. If a value cannot be coerced to an
    integer, a ValueError will be raised.
    """
    return int(getenv(var_name, default))


def str_env(var_name, default=""):
    """
    Get an environment variable as a string.
    This has the same arguments as bool_env.
    """
    return getenv(var_name, default)


def list_env(var_name, default=None):
    """
    Get a comma separated environment variable as a list of strings.
    """
    if default is None:
        default = []
    raw_value = getenv(var_name)
    if raw_value is None:
        return list(default)
    return [item.strip() for item in raw_value.split(",") if item.strip()]


# Basic setup

# Whether or not Confidant is run in debug mode. Never run confidant in debug
# mode outside of development!
DEBUG = bool_env("DEBUG", False)
# The host the WSGI app should use.
HOST = str_env("HOST", "127.0.0.1")
# The port the WSGI app should use.
PORT = int_env("PORT", 8080)
# The directory to use for static content. Relative to Flask's root_path
# (confidant/confidant/). Default serves unbuilt frontend from
# confidant/public/. Set to '../dist' to serve the built frontend from
# confidant/dist/.
STATIC_FOLDER = str_env("STATIC_FOLDER", "../public")

# A custom endpoint url for KMS, for use in development
KMS_URL = str_env("KMS_URL", None)

# Whether Confidant should expect tenant-aware auth context. When disabled,
# the application behaves as a single-tenant system and uses a fixed tenant id.
MULTI_TENANT = bool_env("MULTI_TENANT", False)

# Bootstrapping

# A base64 encoded and KMS encrypted YAML string that contains secrets that
# confidant should use for its own secrets. The blob should be generated using
# confidant's generate_secrets_bootstrap script via manage.py. It uses the
# KMS_MASTER_KEY for decryption.
# If SECRETS_BOOTSTRAP starts with file://, then it will load the blob from a
# file, rather than reading the blob from the environment.
SECRETS_BOOTSTRAP = str_env("SECRETS_BOOTSTRAP")
encrypted_settings = EncryptedSettings(SECRETS_BOOTSTRAP, KMS_URL)

# JWT authentication

# Standard JWKS endpoint used to validate JWTs. Must be a JSON endpoint
# returning a JWK set.
JWKS_URL = str_env("JWKS_URL", "")
# Algorithms we allow for JWT signing.
ALLOWED_JWT_ALGORITHMS = list_env(
    "ALLOWED_JWT_ALGORITHMS",
    ["RS256", "ES256", "ES512"],
)
# The request header from which the JWT is read.
JWT_HEADER_NAME = str_env("JWT_HEADER_NAME", "Authorization")
# The auth scheme prefix expected in Authorization-style headers.
JWT_HEADER_PREFIX = str_env("JWT_HEADER_PREFIX", "Bearer")
# Optional issuer to validate in the JWT. Leave empty to skip issuer
# validation.
JWT_ISSUER = str_env("JWT_ISSUER", "")
# Optional audience to validate in the JWT. Leave empty to skip audience
# validation.
JWT_AUDIENCE = str_env("JWT_AUDIENCE", "")
# The JWT claim that contains the token issuer.
JWT_ISS_CLAIM = str_env("JWT_ISS_CLAIM", "iss")
# The JWT claim that contains the subject identifier.
JWT_SUB_CLAIM = str_env("JWT_SUB_CLAIM", "sub")
# The JWT claim that contains the user's email.
JWT_EMAIL_CLAIM = str_env("JWT_EMAIL_CLAIM", "email")
# The JWT claim that contains the tenant id in multi-tenant mode.
JWT_TENANT_ID_CLAIM = str_env("JWT_TENANT_ID_CLAIM", "tenant_id")
# The JWT claim that contains the principal's group ids.
JWT_GROUPS_CLAIM = str_env("JWT_GROUPS_CLAIM", "groups")
# The claim used to differentiate between end-user and service principals.
JWT_PRINCIPAL_TYPE_CLAIM = str_env("JWT_PRINCIPAL_TYPE_CLAIM", "principal_type")
# The principal type value that represents a user.
JWT_USER_TYPE_VALUE = str_env("JWT_USER_TYPE_VALUE", "user")
# The principal type value that represents a service.
JWT_SERVICE_TYPE_VALUE = str_env("JWT_SERVICE_TYPE_VALUE", "service")
# Allowed principal types.
JWT_ALLOWED_PRINCIPAL_TYPES = list_env(
    "JWT_ALLOWED_PRINCIPAL_TYPES",
    [JWT_USER_TYPE_VALUE, JWT_SERVICE_TYPE_VALUE],
)
# The claim used as the normalized principal name for user tokens.
JWT_USER_PRINCIPAL_CLAIM = str_env("JWT_USER_PRINCIPAL_CLAIM", JWT_EMAIL_CLAIM)
# The claim used as the normalized principal name for service tokens.
JWT_SERVICE_PRINCIPAL_CLAIM = str_env(
    "JWT_SERVICE_PRINCIPAL_CLAIM",
    JWT_SUB_CLAIM,
)

# OIDC configuration surfaced to the frontend so it can acquire JWTs.
OIDC_AUTHORITY = str_env("OIDC_AUTHORITY", "")
OIDC_CLIENT_ID = str_env("OIDC_CLIENT_ID", "")
OIDC_REDIRECT_URI = str_env("OIDC_REDIRECT_URI", "")
OIDC_SCOPE = str_env("OIDC_SCOPE", "openid email")

# SSL redirection and HSTS

# Whether or not to redirect to https and to set HSTS. It's highly recommended
# to run confidant with HTTPS or behind an ELB with SSL termination enabled.
SSLIFY = bool_env("SSLIFY", True)

# General storage

# Set the DynamoDB to something non-standard. This can be used for local
# development. Doesn't normally need to be set.
# Example: http://localhost:8000
DYNAMODB_URL = str_env("DYNAMODB_URL")
# The DynamoDB table to use for storage.
# Example: mydynamodbtable
DYNAMODB_TABLE = str_env("DYNAMODB_TABLE")
# Legacy setting for the old separate-table archive layout. Archives now live
# in the primary single-table design, so this is ignored.
DYNAMODB_TABLE_ARCHIVE = str_env("DYNAMODB_TABLE_ARCHIVE")
# Have Confidant automatically generate the DynamoDB table if it doesn't exist.
# Note that you need to give Confidant's IAM user or role enough privileges for
# this to occur.
DYNAMODB_CREATE_TABLE = bool_env("DYNAMODB_CREATE_TABLE", False)
# Connection pool size for DynamoDB client connections.
DYNAMODB_CONNECTION_POOL_SIZE = int_env(
    "DYNAMODB_CONNECTION_POOL_SIZE",
    100,
)
DYNAMODB_CONNECT_TIMEOUT_SECONDS = int_env(
    "DYNAMODB_CONNECT_TIMEOUT_SECONDS",
    1,
)
DYNAMODB_READ_TIMEOUT_SECONDS = int_env(
    "DYNAMODB_READ_TIMEOUT_SECONDS",
    1,
)
# page limit size for history API endpoints listing
HISTORY_PAGE_LIMIT = int_env("HISTORY_PAGE_LIMIT")
if HISTORY_PAGE_LIMIT == 0:
    HISTORY_PAGE_LIMIT = None

# Encryption

# The KMS key to use for at-rest encryption for secrets in DynamoDB.
# If a key alias is used, rather than an ARN, it must be prefixed with: alias/
KMS_MASTER_KEY = str_env("KMS_MASTER_KEY")

# Graphite events

# A graphite events URL.
# Example: https://graphite.example.com/events/
GRAPHITE_EVENT_URL = str_env("GRAPHITE_EVENT_URL")
# A basic auth username.
# Example: mygraphiteuser
# This setting can be loaded from the SECRETS_BOOTSTRAP.
GRAPHITE_USERNAME = encrypted_settings.register(
    "GRAPHITE_USERNAME", str_env("GRAPHITE_USERNAME")
)
# A basic auth password:
# Example: mylongandsupersecuregraphitepassword
# This setting can be loaded from the SECRETS_BOOTSTRAP.
GRAPHITE_PASSWORD = encrypted_settings.register(
    "GRAPHITE_PASSWORD", str_env("GRAPHITE_PASSWORD")
)

# Statsd metrics

# A statsd host
STATSD_HOST = str_env("STATSD_HOST", "localhost")
# A statsd port
STATSD_PORT = int_env("STATSD_PORT", 8125)

# Webhook configuration

# Endpoint URL to send webhook events to.
WEBHOOK_URL = str_env("WEBHOOK_URL")
# A basic auth username.
# Example: myhookuser
# This setting can be loaded from the SECRETS_BOOTSTRAP.
WEBHOOK_USERNAME = encrypted_settings.register(
    "WEBHOOK_USERNAME", str_env("WEBHOOK_USERNAME")
)
# A basic auth password:
# Example: mylongandsupersecurehookpassword
# This setting can be loaded from the SECRETS_BOOTSTRAP.
WEBHOOK_PASSWORD = encrypted_settings.register(
    "WEBHOOK_PASSWORD", str_env("WEBHOOK_PASSWORD")
)

# Ignore conflicts of credential names in a service
# This is used if you don't mind having more than one of the same key name
# in different credentials associated with a service.
IGNORE_CONFLICTS = bool_env("IGNORE_CONFLICTS", False)

# Customization

# Directory for customization of AngularJS frontend.
CUSTOM_FRONTEND_DIRECTORY = str_env("CUSTOM_FRONTEND_DIRECTORY")

# Custom configuration to bootstrap confidant clients. This
# configuration is in JSON format and can contain anything you'd like to pass
# to the clients.
CLIENT_CONFIG = json.loads(str_env("CLIENT_CONFIG", "{}"))

# Maintenance mode

# Maintenance mode allows you to disable writes from the API, making it
# possible to do migrations or other maintenance actions without worrying
# about writes interfering with your actions. Maintenance mode can be enabled
# either through the MAINTENANCE_MODE_ENABLED configuration option, or through
# a touch file specified via the MAINTENANCE_MODE_TOUCH_FILE configuration
# option.
MAINTENANCE_MODE = bool_env("MAINTENANCE_MODE", False)
MAINTENANCE_MODE_TOUCH_FILE = str_env("MAINTENANCE_MODE_TOUCH_FILE")

# Enforce users to add documentation to their credentials on how to rotate
# them, for easier rotation in the case a credential is expired or compromised.
ENFORCE_DOCUMENTATION = bool_env("ENFORCE_DOCUMENTATION", False)

# Test/Development

# Whether or not authentication is required. Unless doing testing or
# development, this should always be set to True.
USE_AUTH = bool_env("USE_AUTH", True)
# A boolean to enable/disable encryption. This is meant to be used for
# test and development only. If this is disabled it will store unencrypted
# content, rather than encrypted content. This allows you to test
# or do development of features without a KMS key. Even for test and
# development purposes, it's possible to avoid using this setting, by exposing
# AWS credentials to Confidant and giving it access to a KMS key.
# DO NOT DISABLE THIS EXCEPT FOR TEST AND DEVELOPMENT PURPOSES!
USE_ENCRYPTION = bool_env("USE_ENCRYPTION", True)

# boto3 configuration

# Timeout settings for connecting to KMS (see:
# https://botocore.readthedocs.io/en/stable/reference/config.html)
KMS_CONNECTION_TIMEOUT = int_env("KMS_CONNECTION_TIMEOUT", 1)
# Timeout settings for reading from KMS (see:
# https://botocore.readthedocs.io/en/stable/reference/config.html)
KMS_READ_TIMEOUT = int_env("KMS_READ_TIMEOUT", 1)
# Connection pool settings for connecting to KMS (see:
# https://botocore.readthedocs.io/en/stable/reference/config.html)
KMS_MAX_POOL_CONNECTIONS = int_env("KMS_MAX_POOL_CONNECTIONS", 100)

# Must be set to the region the server is running.
AWS_DEFAULT_REGION = str_env("AWS_DEFAULT_REGION", "us-east-1")

# gevent configuration

# Note that it's important to set this environment variable, even though it
# isn't exposed in app.config.
# See: https://github.com/surfly/gevent/issues/468
#
# GEVENT_RESOLVER='ares'

MAXIMUM_ROTATION_DAYS = int_env("MAXIMUM_ROTATION_DAYS")
# Secrets can be "tagged" (eg: FINANCIALLY_SENSITIVE or ADMIN_PRIV)
# Certain tags might never need to be rotated
TAGS_EXCLUDING_ROTATION = json.loads(str_env("TAGS_EXCLUDING_ROTATION", "[]"))
# Secrets with different tags might have different rotation schedules
# We use this config to specify how many days each type of credential should
# be rotated
ROTATION_DAYS_CONFIG = json.loads(str_env("ROTATION_DAYS_CONFIG", "{}"))

# If this is eanbled, update credential.last_decrypted_date
# when credential.credential_pairs is sent back to the client
# in GET /v1/secrets/<ID> to keep track of when a human
# last saw a credential pair
ENABLE_SAVE_LAST_DECRYPTION_TIME = bool_env("ENABLE_SAVE_LAST_DECRYPTION_TIME")


def get(name, default=None):
    """
    Get the value of a variable in the settings module scope.
    """
    if encrypted_settings.registered(name):
        return encrypted_settings.get_secret(name)
    return globals().get(name, default)


# Module that will perform an external ACL check on API endpoints
ACL_MODULE = str_env("ACL_MODULE", "confidant.authnz.rbac:default_acl")
