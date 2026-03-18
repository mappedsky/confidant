# Maintenance

Confidant comes with a number of maintenance scripts that can be used by
admins to handle special maintenance tasks. It's recommended that prior to
running these scripts, that Confidant be put into maintenance mode using the
``MAINTENANCE_MODE`` configuration option, or by using the touch file defined
by the ``MAINTENANCE_MODE_TOUCH_FILE`` configuration option.

## Permanantly archiving disabled credentials to a separate DynamoDB table

By design, confidant never deletes data. You may have a need to permanantly
archive credentials (and revisions of that credential) out of your primary
dynamodb table, so that end-users can no longer access them through the API.

Confidant includes a maintenance script to archive credentials:

```bash
$ pipenv run confidant-admin archive_credentials --help
Usage: confidant-admin archive_credentials [OPTIONS]

  Command to permanently archive credentials to an archive dynamodb table.

Options:
  --days INTEGER  Permanently archive disabled credentials last modified
                  greater than this many days (mutually exclusive with --ids)
  --force         By default, this script runs in dry-run mode, this option
                  forces the run and makes the changes indicated by the dry
                  run
  --ids TEXT      Archive a comma separated list of credential IDs. (mutually
                  exclusive with --days)
  --help          Show this message and exit.
```

To use this, you must have the ``DYNAMODB_TABLE_ARCHIVE`` configuration set,
the table it points at must be created, and IAM settings must be updated to
allow confidant access to this table.

Confidant also has some sanity checks here:

1. The script will not permanently archive a credential if it's currently
   mapped to a service.
1. The script will not permanently archive a credential if it's still enabled.

## Restoring archived credentials back into the primary DynamoDB table

If you've permanently archived a credential, and realise you want it back,
(along with all of its revisions) you can use the ``restore_credentials``
maintenance script:

```bash
$ pipenv run confidant-admin restore_credentials --help
Usage: confidant-admin restore_credentials [OPTIONS]

  Command to restore credentials from the permanent archive dynamodb table
  back into the primary storage table.

Options:
  --force     By default, this script runs in dry-run mode, this option forces
              the run and makes the changes indicated by the dry run
  --ids TEXT  Restore a comma separated list of credential IDs. (mutually
              exclusive with --all)
  --all       Restore all credentials from the permanent archive dynamodb
              table back into the primary store table.
  --help      Show this message and exit.
```

The script will skip any records that already exist in the primary table.
