import json
from datetime import datetime
from datetime import timedelta
from datetime import timezone

from pynamodb.attributes import BinaryAttribute
from pynamodb.attributes import BooleanAttribute
from pynamodb.attributes import JSONAttribute
from pynamodb.attributes import ListAttribute
from pynamodb.attributes import NumberAttribute
from pynamodb.attributes import UnicodeAttribute
from pynamodb.attributes import UTCDateTimeAttribute
from pynamodb.indexes import AllProjection
from pynamodb.indexes import GlobalSecondaryIndex
from pynamodb.models import Model

from confidant import settings
from confidant.services import keymanager
from confidant.services.ciphermanager import CipherManager


class DataTypeDateIndex(GlobalSecondaryIndex):
    class Meta:
        projection = AllProjection()
        read_capacity_units = 10
        write_capacity_units = 10

    data_type = UnicodeAttribute(hash_key=True)
    modified_date = UTCDateTimeAttribute(range_key=True)


class ArchiveDataTypeDateIndex(GlobalSecondaryIndex):
    class Meta:
        projection = AllProjection()
        read_capacity_units = 10
        write_capacity_units = 10

    data_type = UnicodeAttribute(hash_key=True)
    modified_date = UTCDateTimeAttribute(range_key=True)


class SecretBase(Model):
    id = UnicodeAttribute(hash_key=True)
    revision = NumberAttribute()
    data_type = UnicodeAttribute()
    name = UnicodeAttribute()
    secret_pairs = UnicodeAttribute()
    enabled = BooleanAttribute(default=True)
    data_key = BinaryAttribute(legacy_encoding=False)
    # TODO: add cipher_type
    cipher_version = NumberAttribute(null=True)
    metadata = JSONAttribute(default=dict, null=True)
    modified_date = UTCDateTimeAttribute(default=datetime.now)
    modified_by = UnicodeAttribute()
    documentation = UnicodeAttribute(null=True)
    # Classification info (eg: FINANCIALLY_SENSITIVE)
    tags = ListAttribute(default=list)
    last_decrypted_date = UTCDateTimeAttribute(null=True)
    last_rotation_date = UTCDateTimeAttribute(null=True)


class Secret(SecretBase):
    class Meta:
        table_name = settings.DYNAMODB_TABLE
        if settings.DYNAMODB_URL:
            host = settings.DYNAMODB_URL
        region = settings.AWS_DEFAULT_REGION
        connect_timeout_seconds = settings.PYNAMO_CONNECT_TIMEOUT_SECONDS
        read_timeout_seconds = settings.PYNAMO_READ_TIMEOUT_SECONDS
        max_pool_connections = settings.PYNAMO_CONNECTION_POOL_SIZE

    data_type_date_index = DataTypeDateIndex()

    @property
    def secret_keys(self):
        return list(self.decrypted_secret_pairs)

    def _get_decrypted_secret_pairs(self):
        if self.data_type == "secret":
            context = self.id
        else:
            context = self.id.split("-")[0]
        data_key = keymanager.decrypt_datakey(
            self.data_key, encryption_context={"id": context}
        )
        cipher_version = self.cipher_version
        cipher = CipherManager(data_key, cipher_version)
        _secret_pairs = cipher.decrypt(self.secret_pairs)
        _secret_pairs = json.loads(_secret_pairs)
        return _secret_pairs

    @property
    def next_rotation_date(self):
        """
        Return when a secret needs to be rotated for security purposes.
        """
        # Some secrets never need to be rotated
        if self.exempt_from_rotation:
            return None

        # If a secret has never been rotated or been decrypted,
        # immediately rotate
        if self.last_rotation_date is None:
            return datetime.now(timezone.utc)

        if (
            self.last_decrypted_date
            and self.last_decrypted_date > self.last_rotation_date
        ):
            return self.last_decrypted_date

        days = settings.MAXIMUM_ROTATION_DAYS
        for tag in self.tags:
            rotation_days = settings.ROTATION_DAYS_CONFIG.get(tag)
            if rotation_days is None:
                continue
            if days is None or rotation_days < days:
                days = rotation_days
        return self.last_rotation_date + timedelta(days=days)

    @property
    def exempt_from_rotation(self):
        """
        Secrets with certain tags can be exempt from rotation
        """
        return len(set(self.tags) & set(settings.TAGS_EXCLUDING_ROTATION)) > 0

    @property
    def decrypted_secret_pairs(self):
        return self._get_decrypted_secret_pairs()

    @classmethod
    def from_archive_secret(cls, archive_secret):
        return Secret(
            id=archive_secret.id,
            revision=archive_secret.revision,
            data_type=archive_secret.data_type,
            name=archive_secret.name,
            secret_pairs=archive_secret.secret_pairs,
            enabled=archive_secret.enabled,
            data_key=archive_secret.data_key,
            cipher_version=archive_secret.cipher_version,
            metadata=archive_secret.metadata,
            modified_date=archive_secret.modified_date,
            modified_by=archive_secret.modified_by,
            documentation=archive_secret.documentation,
            tags=archive_secret.tags,
            last_decrypted_date=archive_secret.last_decrypted_date,
            last_rotation_date=archive_secret.last_rotation_date,
        )


class SecretArchive(SecretBase):
    class Meta:
        table_name = settings.DYNAMODB_TABLE_ARCHIVE
        if settings.DYNAMODB_URL:
            host = settings.DYNAMODB_URL
        region = settings.AWS_DEFAULT_REGION
        connect_timeout_seconds = settings.PYNAMO_CONNECT_TIMEOUT_SECONDS
        read_timeout_seconds = settings.PYNAMO_READ_TIMEOUT_SECONDS
        max_pool_connections = settings.PYNAMO_CONNECTION_POOL_SIZE

    archive_date = UTCDateTimeAttribute(default=datetime.now)
    data_type_date_index = ArchiveDataTypeDateIndex()

    @classmethod
    def from_secret(cls, secret):
        return SecretArchive(
            id=secret.id,
            revision=secret.revision,
            data_type=secret.data_type,
            name=secret.name,
            secret_pairs=secret.secret_pairs,
            enabled=secret.enabled,
            data_key=secret.data_key,
            cipher_version=secret.cipher_version,
            metadata=secret.metadata,
            modified_date=secret.modified_date,
            modified_by=secret.modified_by,
            documentation=secret.documentation,
            tags=secret.tags,
            last_decrypted_date=secret.last_decrypted_date,
            last_rotation_date=secret.last_rotation_date,
        )
