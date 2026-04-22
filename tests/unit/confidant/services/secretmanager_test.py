import base64

from pytest_mock.plugin import MockerFixture

from confidant.services import secretmanager


def test_get_revision_ids_for_secret():
    secret = type("SecretStub", (), {"id": "1234", "revision": 3})()
    assert secretmanager.get_revision_ids_for_secret(secret) == [
        "1234-1",
        "1234-2",
        "1234-3",
    ]


def test_get_latest_secret_revision():
    res = secretmanager.get_latest_secret_revision("123", 1)
    assert res == 2


def test_check_secret_pair_values(mocker: MockerFixture):
    cred_pairs_success = {"A": "1"}
    cred_pairs_fail = {"A": ["1", "2", "3"]}
    cred_pair_fail_2 = {"A": {"1": "2"}}
    cred_pair_fail_3 = {"A A": {"1": "2"}}
    cred_pair_fail_4 = {"A": "1", "a": "2"}
    result = secretmanager.check_secret_pair_values(cred_pairs_fail)
    assert result[0] is False
    result = secretmanager.check_secret_pair_values(cred_pair_fail_2)
    assert result[0] is False
    result = secretmanager.check_secret_pair_values(cred_pair_fail_3)
    assert result[0] is False
    result = secretmanager.check_secret_pair_values(cred_pair_fail_4)
    assert result[0] is False
    result = secretmanager.check_secret_pair_values(cred_pairs_success)
    assert result[0] is True


def test_encrypt_secret_pairs_encodes_data_key(mocker: MockerFixture):
    mocker.patch(
        "confidant.services.keymanager.create_datakey",
        return_value={"plaintext": b"plaintext", "ciphertext": b"ciphertext"},
    )
    cipher_mock = mocker.patch(
        "confidant.services.secretmanager.CipherManager",
    )
    cipher_mock.return_value.encrypt.return_value = "encrypted-pairs"
    _, data_key, _ = secretmanager._encrypt_secret_pairs(
        "tenant-a",
        "cred-1",
        {"a": "b"},
    )
    assert data_key == base64.b64encode(b"ciphertext").decode("UTF-8")


def test_sanitize_write_items_strips_empty_values():
    items = [
        {
            "Item": {
                "PK": "x",
                "SK": "y",
                "documentation": "",
                "metadata": {},
                "value": "ok",
            },
            "ConditionExpression": "attribute_not_exists(PK)",
        }
    ]

    sanitized = secretmanager._sanitize_write_items(items)

    assert sanitized == [
        {
            "Item": {
                "PK": "x",
                "SK": "y",
                "value": "ok",
            },
            "ConditionExpression": "attribute_not_exists(PK)",
        }
    ]


def test_build_secret_items_uses_raw_secret_id_for_list_item():
    metadata_item, latest_item, version_item, list_item = (
        secretmanager._build_secret_items(
            tenant_id="tenant-a",
            secret_id="apps/payments/prod/db",
            name="Database",
            revision=1,
            secret_keys=["api_key"],
            secret_pairs="encrypted",
            data_key="key",
            cipher_version=3,
            metadata={},
            modified_by="user@example.com",
            documentation=None,
            created_at="2026-04-08T00:00:00+00:00",
        )
    )

    assert metadata_item["SK"] == "#METADATA"
    assert latest_item["SK"] == "#LATEST"
    assert version_item["SK"] == "VERSION#0000000001"
    assert list_item["SK"] == "apps/payments/prod/db"


def test_list_secrets_passes_prefix_to_store(mocker: MockerFixture):
    store_mock = mocker.patch(
        "confidant.services.secretmanager.store.list_secrets",
        return_value={"Items": []},
    )

    secretmanager.list_secrets(
        "tenant-a",
        limit=25,
        page={"PK": "x"},
        prefix="apps/",
    )

    assert store_mock.call_args.kwargs["prefix"] == "apps/"


def test_create_secret_preserves_secret_key_case(mocker: MockerFixture):
    mocker.patch(
        "confidant.services.secretmanager.store.get_secret_latest",
        return_value=None,
    )
    mocker.patch(
        "confidant.services.secretmanager._secret_response_from_item",
        side_effect=lambda item, **kwargs: type(
            "SecretStub",
            (),
            {"secret_keys": item["secret_keys"]},
        )(),
    )
    encrypt_mock = mocker.patch(
        "confidant.services.secretmanager._encrypt_secret_pairs",
        return_value=("encrypted", "data-key", 2),
    )
    put_mock = mocker.patch("confidant.services.secretmanager.store.put_version_bundle")

    secret, error = secretmanager.create_secret(
        tenant_id="tenant-a",
        secret_id="apps/test",
        name="Test secret",
        secret_pairs={"API_KEY": "value"},
        created_by="user@example.com",
    )

    assert error is None
    assert secret.secret_keys == ["API_KEY"]
    assert encrypt_mock.call_args.args[2] == {"API_KEY": "value"}
    write_items = put_mock.call_args.args[0]
    assert write_items[0]["Item"]["secret_keys"] == ["API_KEY"]


def test_update_secret_preserves_secret_key_case(mocker: MockerFixture):
    mocker.patch(
        "confidant.services.secretmanager.store.get_secret_latest",
        return_value={
            "tenant_id": "tenant-a",
            "id": "apps/test",
            "name": "Old name",
            "revision": 1,
            "modified_date": "2026-04-08T00:00:00+00:00",
            "modified_by": "user@example.com",
            "secret_keys": ["OLD_KEY"],
            "secret_pairs": "old-encrypted",
            "data_key": "old-data-key",
            "cipher_version": 2,
        },
    )
    mocker.patch(
        "confidant.services.secretmanager._secret_response_from_item",
        side_effect=lambda item, **kwargs: type(
            "SecretStub",
            (),
            {"secret_keys": item["secret_keys"]},
        )(),
    )
    encrypt_mock = mocker.patch(
        "confidant.services.secretmanager._encrypt_secret_pairs",
        return_value=("encrypted", "data-key", 2),
    )
    put_mock = mocker.patch("confidant.services.secretmanager.store.put_version_bundle")

    secret, error = secretmanager.update_secret(
        tenant_id="tenant-a",
        secret_id="apps/test",
        name="New name",
        created_by="user@example.com",
        secret_pairs={"API_KEY": "value"},
    )

    assert error is None
    assert secret.secret_keys == ["API_KEY"]
    assert encrypt_mock.call_args.args[2] == {"API_KEY": "value"}
    write_items = put_mock.call_args.args[0]
    assert write_items[0]["Item"]["secret_keys"] == ["API_KEY"]
