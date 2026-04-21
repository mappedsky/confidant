from datetime import datetime, timezone

from confidant.services.dynamodbstore import DynamoDBConfidantStore, _serialize_item


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
        "items": ["", "tag"],
        "nested": (None, "", "x"),
    }

    serialized = _serialize_item(item)

    assert "documentation" not in serialized
    assert serialized["metadata"]["M"] == {"keep": {"S": "value"}}
    assert serialized["items"]["L"] == [{"S": "tag"}]
    assert serialized["nested"]["L"] == [{"S": "x"}]


def test_serialize_item_strips_empty_containers():
    item = {
        "metadata": {},
        "items": [],
        "nested": {"empty": []},
    }

    serialized = _serialize_item(item)

    assert serialized == {}


def test_serialize_item_strips_empty_sets_and_bytes():
    item = {
        "items": set(),
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


def test_serialize_item_strips_empty_dict_keys_and_stringifies_keys() -> None:
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


def test_list_groups_for_secret_matches_policy_glob(mocker):
    list_groups_mock = mocker.patch.object(
        DynamoDBConfidantStore,
        "list_groups",
        return_value={
            "Items": [
                {
                    "id": "policy-a",
                    "policies": {"apps/*": ["decrypt"]},
                },
                {
                    "id": "policy-b",
                    "policies": {"other/*": ["decrypt"]},
                },
            ]
        },
    )

    store = DynamoDBConfidantStore()
    groups = store.list_groups_for_secret("singletenant", "apps/service-a")

    list_groups_mock.assert_called_once_with("singletenant")
    assert [group["id"] for group in groups] == ["policy-a"]


def test_list_secrets_uses_prefix_query(mocker):
    query_mock = mocker.patch(
        "confidant.services.dynamodbstore._query_items",
        return_value={"Items": []},
    )

    store = DynamoDBConfidantStore()
    store.list_secrets("singletenant", prefix="apps/")

    assert query_mock.call_args.kwargs["begins_with_sk"] == "apps/"
