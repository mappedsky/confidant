import json
import logging
import sys

import click
from pynamodb.attributes import Attribute
from pynamodb.attributes import UnicodeAttribute
from pynamodb.constants import STRING_SET
from pynamodb.models import Model

from confidant.models.group import Group

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.INFO)


def is_old_unicode_set(values):
    if not values:
        return False
    return sum([x.startswith('"') for x in values]) > 0


class SetMixin:
    """
    Adds (de)serialization methods for sets
    """

    def serialize(self, value):
        """
        Serializes a set

        Because dynamodb doesn't store empty attributes,
        empty sets return None
        """
        if value is not None:
            try:
                iter(value)
            except TypeError:
                value = [value]
            if len(value):
                return [json.dumps(val) for val in sorted(value)]
        return None

    def deserialize(self, value):
        """
        Deserializes a set
        """
        if value and len(value):
            return {json.loads(val) for val in value}


class NewUnicodeSetAttribute(SetMixin, Attribute):
    """
    A unicode set
    """

    attr_type = STRING_SET
    null = True

    def element_serialize(self, value):
        """
        This serializes unicode / strings out as unicode strings.
        It does not touch the value if it is already a unicode str
        :param value:
        :return:
        """
        if isinstance(value, str):
            return value
        return str(value)

    def element_deserialize(self, value):
        return value

    def serialize(self, value):
        if value is not None:
            try:
                iter(value)
            except TypeError:
                value = [value]
            if len(value):
                return [self.element_serialize(val) for val in sorted(value)]
        return None

    def deserialize(self, value):
        if value and len(value):
            return {self.element_deserialize(val) for val in value}


class GeneralGroupModel(Model):
    class Meta(Group.Meta):
        pass

    id = UnicodeAttribute(hash_key=True)
    secrets = NewUnicodeSetAttribute(default=set(), null=True)


@click.command()
def migrate_group_set_attribute():
    """
    Migrate UnicodeSetAttribute in Group
    """
    total = 0
    fail = 0
    logger.info("Migrating UnicodeSetAttribute in Group")
    for group in Group.data_type_date_index.query("group"):
        group.save()
        new_group = GeneralGroupModel.get(group.id)
        if is_old_unicode_set(new_group.secrets):
            fail += 1
        total += 1
    logger.info(f"Fail: {fail}, Total: {total}")
