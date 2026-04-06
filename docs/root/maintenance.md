# Maintenance

Confidant comes with a number of maintenance scripts that can be used by
admins to handle special maintenance tasks. It's recommended that prior to
running these scripts, that Confidant be put into maintenance mode using the
``MAINTENANCE_MODE`` configuration option, or by using the touch file defined
by the ``MAINTENANCE_MODE_TOUCH_FILE`` configuration option.

## Archiving and restoring deleted records

By design, Confidant moves deleted secrets and groups into archive partitions
inside the primary DynamoDB table rather than removing them outright. The
archive records are stored in the existing single-table layout; no separate
archive table is required.

When a secret or group is deleted through the API or web UI, Confidant archives
the current record and its version history under the archive key space before
removing the active records.

Archived secrets and groups can be restored by creating a new current version
from a prior revision using the version restore endpoints exposed in the API
and UI. There is no longer a standalone maintenance CLI for bulk archive or
bulk restore operations.
