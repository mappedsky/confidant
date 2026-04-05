from datetime import datetime

from pynamodb.attributes import BooleanAttribute
from pynamodb.attributes import NumberAttribute
from pynamodb.attributes import UnicodeAttribute
from pynamodb.attributes import UTCDateTimeAttribute
from pynamodb.indexes import AllProjection
from pynamodb.indexes import GlobalSecondaryIndex
from pynamodb.models import Model

from confidant import settings
from confidant.models.non_null_unicode_set_attribute import (
    NonNullUnicodeSetAttribute,
)


class DataTypeDateIndex(GlobalSecondaryIndex):
    class Meta:
        projection = AllProjection()
        read_capacity_units = 10
        write_capacity_units = 10

    data_type = UnicodeAttribute(hash_key=True)
    modified_date = UTCDateTimeAttribute(range_key=True)


class Group(Model):
    class Meta:
        table_name = settings.DYNAMODB_TABLE
        if settings.DYNAMODB_URL:
            host = settings.DYNAMODB_URL
        region = settings.AWS_DEFAULT_REGION
        connect_timeout_seconds = settings.PYNAMO_CONNECT_TIMEOUT_SECONDS
        read_timeout_seconds = settings.PYNAMO_READ_TIMEOUT_SECONDS
        max_pool_connections = settings.PYNAMO_CONNECTION_POOL_SIZE

    id = UnicodeAttribute(hash_key=True)
    data_type = UnicodeAttribute()
    data_type_date_index = DataTypeDateIndex()
    revision = NumberAttribute()
    enabled = BooleanAttribute(default=True)
    secrets = NonNullUnicodeSetAttribute(default=set)
    account = UnicodeAttribute(null=True)
    modified_date = UTCDateTimeAttribute(default=datetime.now)
    modified_by = UnicodeAttribute()

    def equals(self, other_group):
        if set(self.secrets) != set(other_group.secrets):
            return False
        return True

    def diff(self, other_group):
        if self.revision == other_group.revision:
            return {}
        elif self.revision > other_group.revision:
            old = other_group
            new = self
        else:
            old = self
            new = other_group
        diff = {}
        if old.enabled != new.enabled:
            diff["enabled"] = {"added": new.enabled, "removed": old.enabled}
        if set(old.secrets) != set(new.secrets):
            diff["secrets"] = self._diff_list(
                old.secrets,
                new.secrets,
            )
        diff["modified_by"] = {
            "added": new.modified_by,
            "removed": old.modified_by,
        }
        diff["modified_date"] = {
            "added": new.modified_date,
            "removed": old.modified_date,
        }
        return diff

    def _diff_list(self, old, new):
        diff = {}
        removed = []
        added = []
        for key in old:
            if key not in new:
                removed.append(key)
        for key in new:
            if key not in old:
                added.append(key)
        if removed:
            diff["removed"] = sorted(removed)
        if added:
            diff["added"] = sorted(added)
        return diff
