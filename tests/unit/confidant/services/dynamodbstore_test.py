from datetime import datetime, timezone

from confidant.services.dynamodbstore import _serialize_item


def test_serialize_item_converts_datetime_to_string():
    item = {
        "created_at": datetime(2026, 4, 1, 5, 15, 55, tzinfo=timezone.utc),
        "name": "example",
    }

    serialized = _serialize_item(item)

    assert serialized["created_at"]["S"] == "2026-04-01T05:15:55+00:00"
    assert serialized["name"]["S"] == "example"


def test_serialize_item_strips_none_and_empty_strings():
    item = {
        "documentation": "",
        "metadata": {"empty": "", "keep": "value"},
        "tags": ["", "tag"],
        "nested": (None, "", "x"),
    }

    serialized = _serialize_item(item)

    assert "documentation" not in serialized
    assert serialized["metadata"]["M"] == {"keep": {"S": "value"}}
    assert serialized["tags"]["L"] == [{"S": "tag"}]
    assert serialized["nested"]["L"] == [{"S": "x"}]


def test_serialize_item_strips_empty_containers():
    item = {
        "metadata": {},
        "tags": [],
        "nested": {"empty": []},
    }

    serialized = _serialize_item(item)

    assert serialized == {}


def test_serialize_item_strips_empty_sets_and_bytes():
    item = {
        "tags": set(),
        "nested": {"empty": frozenset()},
        "blob": b"",
    }

    serialized = _serialize_item(item)

    assert serialized == {}


def test_serialize_item_encodes_non_empty_bytes():
    item = {"blob": b"abc"}

    serialized = _serialize_item(item)

    assert serialized["blob"]["S"] == "YWJj"


def test_serialize_item_coerces_unknown_scalars_to_strings():
    class CustomValue:
        def __str__(self):
            return "custom-value"

    item = {"value": CustomValue()}

    serialized = _serialize_item(item)

    assert serialized["value"]["S"] == "custom-value"


def test_serialize_item_strips_empty_dict_keys_and_stringifies_non_string_keys():
    item = {
        "metadata": {
            "": "drop",
            " keep ": "value",
            1: "one",
        }
    }

    serialized = _serialize_item(item)

    assert serialized["metadata"]["M"] == {
        "keep": {"S": "value"},
        "1": {"S": "one"},
    }
