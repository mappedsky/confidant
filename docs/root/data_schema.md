# DynamoDB Data Schema

Confidant stores secrets, groups, and archived deletions in a single DynamoDB
table. Each resource uses a stable partition key with separate items for
metadata, the latest revision, and historical revisions.

Secret items include:

* id: secret identifier (string)
* revision: incrementing integer
* name: user-defined friendly name
* secret\_pairs: encrypted key/value data
* data\_key: encrypted data key used for secret\_pairs
* metadata: clear-text metadata map
* modified\_date: auto-generated timestamp

Group items include:

* id: group identifier (string)
* revision: incrementing integer
* policies: map of secret ids or globs to allowed actions
* modified\_date: auto-generated timestamp

Deleted secrets and groups are copied into archive partitions in the same table
before the active records are removed.

## At-rest encryption model

All metadata in Confidant is stored in clear text, but secret pairs in
secrets are stored encrypted at-rest.

Confidant uses a configured KMS master key to generate 32-byte data keys.
The encrypted data keys are stored in DynamoDB along with the secret.
The decrypted data keys are kept in memory in the confidant web service
for caching purposes.

Secret pairs are encrypted with AES-256-GCM using a fresh 12-byte nonce per
encryption. The nonce, ciphertext, and 16-byte authentication tag are
concatenated and stored as a URL-safe base64 string. The `cipher_version`
field on each DynamoDB item records the format version so future migrations
can distinguish between cipher schemes.

When secrets are created or updated, their secret pair information is
encrypted and the data key used to encrypt the pair is recorded with
the secret, in its encrypted form. When secrets are fetched, their
secret pair is decrypted using the data key associated with the secret.
For each secret decryption we make a call to KMS, if the plaintext data key
isn't available in memory.
