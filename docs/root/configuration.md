# Configuration

Confidant is primarily configured through environment variables. The list of
all available configuration options can be found in the settings.py file.

## Docker vs bash

Note that below the format of the configuration is given in bash format for
defining and exporting environment variables. Docker environment files have a
slightly different format than bash. Here's an example of the difference:

In bash format:

```bash
export MY_VARIABLE='MY_VALUE'
```

In docker env file format, you don't export the variable, and the value
shouldn't be quoted, since everything after the equal sign is considered part
of the value. So, in a docker environment file, you'd define the same variable
and value like this:

In docker format:

```
MY_VARIABLE=MY_VALUE
```

## Environment configuration

This is the minimum configuration needed to use Confidant:

```bash
# The region our service is running in.
export AWS_DEFAULT_REGION='us-east-1'
# The DynamoDB table name for storage.
export DYNAMODB_TABLE='confidant-production'
# Auto-generate the dynamodb table.
export DYNAMODB_CREATE_TABLE=true
# Set the gevent resolver to ares; see:
#   https://github.com/surfly/gevent/issues/468
# export GEVENT_RESOLVER='ares'
# The KMS key used for at-rest encryption in DynamoDB.
export KMS_MASTER_KEY='alias/confidant-production'
# JWT / OIDC auth
export JWKS_URL='https://idp.example.com/application/o/confidant/jwks/'
export OIDC_AUTHORITY='https://idp.example.com/application/o/confidant'
export OIDC_CLIENT_ID='confidant'
# SESSION_SECRET can be loaded via SECRETS_BOOTSTRAP
export SESSION_SECRET='aBVmJA3zv6zWGjrYto135hkdox6mW2kOu7UaXIHK8ztJvT8w5O'
# The IP address to listen on.
export HOST='0.0.0.0'
# The port to listen on.
export PORT='80'
# Trust X-Forwarded-Proto from any SSL termination server
export FORWARDED_ALLOW_IPS='*'
```

### gunicorn configuration for SSL termination support

We assume confidant is always run behind a trusted SSL termination load
balancer. As such, confidant will run as http:// and gunicorn will need to trust
X-Forwarded-Proto to know that it's running behind a terminator.

To configure this via an environment variable:

```bash
# Environment for gunicorn
export FORWARDED_ALLOW_IPS='*'
```

If the environment variable doesn't work, you can configure this through a CLI
argument to gunicorn:

```bash
# CLI flag for gunicorn
gunicorn confidant.wsgi:app -k gevent --forwarded-allow-ips=*
```

### JWT / OIDC authentication configuration

Confidant now authenticates every API request with a Bearer JWT and validates
that token against a JWKS endpoint. The browser UI uses OIDC Authorization Code
with PKCE to acquire the token. Any standard OIDC provider can be used; the local
development stack ships with Authentik.

The backend owns the OIDC settings and exposes them to the SPA through
`GET /v1/auth_config` and `GET /v1/client_config`. The frontend should not
hardcode provider-specific endpoints.

```bash
# JWKS endpoint used by the backend to validate JWTs
export JWKS_URL='https://idp.example.com/application/o/confidant/jwks/'

# OIDC settings used by the backend and exposed to the frontend via the API
export OIDC_AUTHORITY='https://idp.example.com/application/o/confidant'
export OIDC_CLIENT_ID='confidant'
export OIDC_REDIRECT_URI='https://confidant.example.com/auth/callback'
export OIDC_SCOPE='openid email profile'

# Optional JWT validation constraints
export JWT_ISSUER=''
export JWT_AUDIENCE=''

# Claim names used to normalize the current principal
export JWT_EMAIL_CLAIM='email'
export JWT_SUB_CLAIM='sub'
export JWT_TENANT_ID_CLAIM='tenant_id'
export JWT_PRINCIPAL_TYPE_CLAIM='principal_type'
export JWT_USER_PRINCIPAL_CLAIM='email'
export JWT_SERVICE_PRINCIPAL_CLAIM='sub'

# The IdP must explicitly mark whether the token represents a user or a service
export JWT_USER_TYPE_VALUE='user'
export JWT_SERVICE_TYPE_VALUE='service'
export JWT_ALLOWED_PRINCIPAL_TYPES='user,service'
```

### Session settings

JWT authentication is stateless and no longer relies on server-managed login
sessions or CSRF cookies. The remaining Flask session
settings are only relevant to the application's general cookie/session
configuration and are not part of the authentication flow.

### Disabling credential conflict checks

By default confidant will ensure that credentials mapped to a service don't
have any conflicting credential pair keys. These checks occur when mapping
credentials to a service, or when modifying credentials that are mapped to a
service. To disable this check:

```bash
export IGNORE_CONFLICTS='True'
```

### statsd metrics

Confidant can track some stats via statsd. By default it's set to send stats to
statsd on localhost on port 8125.

```bash
export STATSD_HOST='mystatshost.example.com'
export STATSD_PORT='8125'
```

### Sending graphite events

Confidant can also send graphite events on secret updates or changes in service
mappings:

```bash
export GRAPHITE_EVENT_URL='https://graphite.example.com/events/'
export GRAPHITE_USERNAME='mygraphiteuser'
# GRAPHITE_PASSWORD can be loaded via SECRETS_BOOTSTRAP
export GRAPHITE_PASSWORD='mylongandsupersecuregraphitepassword'
```

### Google authentication user restrictions

It's possible to restrict access to a subset of users that authenticate
using Google authentication:

```bash
export USERS_FILE='/etc/confidant/users.yaml'
export USER_EMAIL_SUFFIX='@example.com'
```

In the above configuration, Confidant will limit authentication to users with
the email domain @example.com. Additionally, Confidant will look in the
users.yaml file for a list of email addresses allowed to access Confidant.

### Auth token lifetime

It's possible to limit the lifetime of KMS authentication tokens. By default
Confidant limits token lifetime to 60 minutes, to ensure that tokens are being
rotated. To change this, you can use the following option:

```bash
# Limit token lifetime to 10 minutes.
export AUTH_TOKEN_MAX_LIFETIME='10'
```

### Frontend configuration

If you're using the generated, minified output in the dist directory, you
need to tell confidant to change its static folder:

```bash
export STATIC_FOLDER='dist'
```

It's possible to customize portions of the angularjs application.
Currently you can add a documentation section to the credential details view.
We'd like to make more customization available. Please open a github issue with
specific customizations you'd like focused on first. The custom js/css/html
will be served from a directory you specify:

```bash
export CUSTOM_FRONTEND_DIRECTORY='/srv/confidant-static'
```

### Development and testing settings

There's a few settings that are meant for development or testing purposes only
and should never be used in production:

```bash
# Disable all forms of authentication.
# NEVER USE THIS IN PRODUCTION!
export USE_AUTH=false
# Disable any use of at-rest encryption.
# NEVER USE THIS IN PRODUCTION!
export USE_ENCRYPTION=false
# Disable SSLify
# NEVER USE THIS IN PRODUCTION!
export SSLIFY=false
# Enable debug mode, which will also disable SSLify.
# NEVER USE THIS IN PRODUCTION!
export DEBUG=true
```

### Bootstrapping Confidant's own secrets

It's possible for confidant to load its own secrets from a KMS encrypted base64
encoded YAML dict. This dict can be generated (and decrypted) through a
confidant script:

```bash
cd /srv/confidant
source venv/bin/activate

# Encrypt the data
python manage.py generate_secrets_bootstrap --in unencrypted_dict.yaml --out encrypted_dict.yaml.enc
export SECRETS_BOOTSTRAP=`cat encrypted_dict.yaml.enc`

# Get a decrypted output of the yaml data
python manage.py decrypt_secrets_bootstrap
```

### Confidant client configuration

Confidant exposes some data to its clients via a flask endpoint. It's possible
to expose additional custom data to clients through the server's configuration:

```bash
export CLIENT_CONFIG='{"cipher_type":"fernet","cipher_version":"2","store_credential_keys":true}'
```

The native client, or custom clients can use this data to help configure
themselves.

### Maintenance mode settings

If you need to disable all writes via the API, for maintenance actions, or
any other reason, Confidant has a maintenance mode that can be enabled.
There's a couple ways to put Confidant into maintenance mode. An explicit
setting is available:

```bash
export MAINTENANCE_MODE='True'
```

There's also a runtime setting, that allows you to enable/disable maintenance
mode by using a touch file. You'll need to configure the location of this
touch file via settings:

```bash
export MAINTENANCE_MODE_TOUCH_FILE='/run/confidant/maintenance'
```

To enable maintenance mode, create the file:

```bash
touch /run/confidant/maintenance
```

To disable maintenance mode, remove the file:

```bash
rm /run/confidant/maintenance
```

### Confidant performance settings

Confidant comes setup to perform well by default, but it's possible you may
find some of these settings too aggressive, or you may have enough clients or
services that the defaults aren't high enough.

The primary performance setting is for authentication token caching, and is set
to 4096. This should be set to something near your total number of clients with
unique authentication tokens. Assuming every client has a unique token, it
should be equal to greater than your number of clients. This cache avoids calls
to KMS for authentication, reducing latency and reducing likelyhood of
ratelimiting from KMS. The following configuration can adjust this:

```
export KMS_AUTH_TOKEN_CACHE_SIZE=4096
```

Confidant has a couple settings for tuning pynamodb performance. By default
confidant is pretty aggressive with pynamodb timeouts, setting the default
timeout to 1s. This is to fail fast and retry, rather than waiting on a blocked
request that could be general networking failures, attempting to avoid request
pileups. If this setting is too aggressive, you can adjust it via:

```
export PYNAMO_CONNECT_TIMEOUT_SECONDS=1
export PYNAMO_READ_TIMEOUT_SECONDS=1
```

To avoid recreating connections to dynamodb on each request, we open a larger
than default number of pooled connections to dynamodb. Our default is 100. The
number of connections should be greater than or equal to the number of
concurrent requests per worker. To adjust this:

```
export PYNAMO_CONNECTION_POOL_SIZE=100
```

Similar to the performance tuning for dynamodb, we also have similar tuning
settings for KMS. For both connection and read timeouts, we aggressively set
the timeout to be 1s, since we assume any request that takes this long is
related to some network failure. To adjust these settings:

```
export KMS_CONNECTION_TIMEOUT=1
export KMS_READ_TIMEOUT=1
```

We also increase the default connection pool to KMS. This should be greater
than or equal to the number of concurrent requests per worker. To adjust this:

```
export KMS_MAX_POOL_CONNECTIONS=100
```

### Settings for local development

It's possible to point confidant at local versions of AWS services for testing.

```
# The local versions of the AWS services don't use real AWS credentials, so
# you probably want to fake these
AWS_ACCESS_KEY_ID=1
AWS_SECRET_ACCESS_KEY=1
# The url to your local dynamodb server
DYNAMODB_URL=http://dynamodb:8080
# The url to your local kms server
KMS_URL=http://kms:8080
```

## KMS key policy configuration

Confidant needs a KMS key policy for the at-rest `KMS_MASTER_KEY`.

Here's an example key policy for the at-rest encryption key, `KMS_MASTER_KEY`, assuming the
above configuration. Note the following:

1. The "Enable IAM User Permissions" policy ensures that IAM users in your account
   that have the proper IAM permissions can manage this key. This is here to
   ensure you don't lock yourself out of the key.
1. The "Allow access for Key Administrators" policy ensures that a special IAM
   user can manage the KMS key.
1. The "Allow use of the key" policy ensures that confidant can use the key.

```json
{
  "Version" : "2012-10-17",
  "Id" : "key-consolepolicy-1",
  "Statement" : [ {
    "Sid" : "Enable IAM User Permissions",
    "Effect" : "Allow",
    "Principal" : {
      "AWS" : "arn:aws:iam::12345:root"
    },
    "Action" : "kms:*",
    "Resource" : "*"
  }, {
    "Sid" : "Allow access for Key Administrators",
    "Effect" : "Allow",
    "Principal" : {
      "AWS" : "arn:aws:iam::12345:user/myadminuser"
    },
    "Action" : [ "kms:Describe*", "kms:List*", "kms:Create*", "kms:Revoke*",
"kms:Enable*", "kms:Get*", "kms:Disable*", "kms:Delete*", "kms:Put*",
"kms:Update*" ],
    "Resource" : "*"
  }, {
    "Sid" : "Allow use of the key",
    "Effect" : "Allow",
    "Principal" : {
      "AWS" : "arn:aws:iam::12345:role/confidant-production"
    },
    "Action" : [ "kms:Decrypt", "kms:GenerateDataKey*", "kms:ReEncrypt*",
"kms:DescribeKey", "kms:Encrypt" ],
    "Resource" : "*"
  } ]
}
```

Here's an example key policy for the authentication key, AUTH\_KEY, assuming the
above configuration. Note the following:

1. The "Enable IAM User Permissions" policy ensures that IAM users in your account
   that have the proper IAM permissions can manage this key. This is here to
   ensure you don't lock yourself out of the key.
1. The "Allow access for Key Administrators" policy ensures that a special IAM
   user can manage the KMS key.
1. The "Allow use of the key" policy ensures that confidant can use the key.
1. The "Allow attachment of persistent resources" policy ensures that confidant
   can add and revoke grants for the auth key, which is necessary to give
   access to context specific encrypt and decrypt calls for service principals.


```json
{
  "Version" : "2012-10-17",
  "Id" : "key-consolepolicy-1",
  "Statement" : [ {
    "Sid" : "Enable IAM User Permissions",
    "Effect" : "Allow",
    "Principal" : {
      "AWS" : "arn:aws:iam::12345:root"
    },
    "Action" : "kms:*",
    "Resource" : "*"
  }, {
    "Sid" : "Allow access for Key Administrators",
    "Effect" : "Allow",
    "Principal" : {
      "AWS" : "arn:aws:iam::12345:user/myadminuser"
    },
    "Action" : [ "kms:Describe*", "kms:List*", "kms:Create*", "kms:Revoke*",
"kms:Enable*", "kms:Get*", "kms:Disable*", "kms:Delete*", "kms:Put*",
"kms:Update*" ],
    "Resource" : "*"
  }, {
    "Sid" : "Allow use of the key",
    "Effect" : "Allow",
    "Principal" : {
      "AWS" : "arn:aws:iam::12345:role/confidant-production"
    },
    "Action" : [ "kms:Decrypt", "kms:GenerateDataKey*", "kms:ReEncrypt*",
"kms:DescribeKey", "kms:Encrypt" ],
    "Resource" : "*"
  } ]
}
```

Allow Confidant to generate random data from KMS:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": [
                "kms:GenerateRandom"
            ],
            "Effect": "Allow",
            "Resource": "*"
        }
    ]
}
```

Allow Confidant access to its DynamoDB table. We restrict DeleteTable access,
because the application should never be able to do that.

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": [
                "dynamodb:*"
            ],
            "Effect": "Allow",
            "Resource": [
                "arn:aws:dynamodb:*:*:table/confidant-production",
                "arn:aws:dynamodb:*:*:table/confidant-production/*"
            ]
        },
        {
            "Action": [
                "dynamodb:DeleteTable"
            ],
            "Effect": "Deny",
            "Resource": [
                "arn:aws:dynamodb:*:*:table/confidant-production"
            ]
        }
    ]
}
```

## Confidant DynamoDB table configuration

You'll need to create a dynamodb with two global indexes:

```
hash id: id
hash key data type: S

global indexes:

data_type_date_index:
  hash key: data_type
  hash key data type: S
  range key: modified_date
  range key data type: S

data_type_revision_index:
  hash key: data_type
  hash key data type: S
  range key: revision
  range key data type: N
```

Provisioned read/write units can be relative low on both the primary table and
the indexes. See your usage in cloudwatch and increase throughput as necessary.
