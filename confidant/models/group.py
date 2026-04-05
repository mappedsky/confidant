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
