# DynamoDB Data Schema

We define __secret__, __archive-secret__, __service__, and
__archive_service__. __secret__ and __service__ are the current revision of
a secret, or a service. __archive-secret__ and __archive_service__ are
archived revisions of passwords and groups and are append-only.

When a secret or a service is updated, it is added to the archive and the
current revision is modified to reflect the newest revision. If the item isn't
saved to the archive, the request will fail and the state of the system stays
the same.

__secret__

* id: uuid4 (string)
* data-type: 'secret' (string)
* revision: incrementing integer (integer)
* name: user-defined friendly name (string)
* secret\_pairs: dict with key/val pairs (string)
* enabled: active/deprecated (boolean)
* data\_key: encrypted data key used to encrypt the secret\_pairs (binary)
* modified\_date: auto-generated date (datetime)

__archive-secret__

* id: uuid4-revision (string)
* data-type: 'archive-secret' (string)
* revision: incrementing integer (current revision + 1) (integer)
* name: user-defined friendly name (string)
* secret\_pairs: dict with key/val pairs (string)
* enabled: active/deprecated (boolean)
* data\_key: encrypted data key used to encrypt the secret\_pairs (binary)
* modified\_date: auto-generated date (datetime)

__service__

* id: user-defined group identifier (string)
* data-type: 'service' (string)
* revision: incrementing integer (integer)
* secrets: list of secret ids (string set)
* enabled: active/deprecated (boolean)
* modified\_date: auto-generated date (datetime)

__archive-service__

* id: user-defined group identifier (string)
* data-type: 'service' (string)
* revision: incrementing integer (current revision + 1) (integer)
* secrets: list of secret ids (string set)
* enabled: active/deprecated (boolean)
* modified\_date: auto-generated date (datetime)

## At-rest encryption model

All metadata in Confidant is stored in clear text, but secret pairs in
secrets are stored encrypted at-rest.

Confidant uses a configured KMS master key to generate data keys. The
encrypted data keys are stored in DynamoDB along with the secret.
The decrypted data keys are kept in memory in the confidant web service
for caching purposes.

When secrets are created or updated, their secret pair information is
encrypted and the data key used to encrypt the pair is recorded with
the secret, in its encrypted form. When secrets are fetched, their
secret pair is decrypted using the data key associated with the secret.
For each secret decryption we make a call to KMS, if the plaintext data key
isn't available in memory.
