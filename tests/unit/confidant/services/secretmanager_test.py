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
    result = secretmanager.check_secret_pair_values(cred_pairs_fail)
    assert result[0] is False
    result = secretmanager.check_secret_pair_values(cred_pair_fail_2)
    assert result[0] is False
    result = secretmanager.check_secret_pair_values(cred_pair_fail_3)
    assert result[0] is False
    result = secretmanager.check_secret_pair_values(cred_pairs_success)
    assert result[0] is True


def test_lowercase_secret_pairs():
    test = {"A": "123", "B": "345", "C": "678"}

    expected = {"a": "123", "b": "345", "c": "678"}
    res = secretmanager.lowercase_secret_pairs(test)
    assert res == expected


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


def test_save_last_decryption_time_updates_store_and_item(
    mocker: MockerFixture,
):
    update_target_prefix = "confidant.services.secretmanager.store."
    update_target = update_target_prefix + "update_secret_last_decrypted_date"
    update_mock = mocker.patch(
        update_target,
    )
    mocker.patch("confidant.settings.ENABLE_SAVE_LAST_DECRYPTION_TIME", True)

    item = {"id": "cred-1", "tenant_id": "tenant-a"}
    updated = secretmanager._save_last_decryption_time(
        "tenant-a",
        "cred-1",
        item,
    )

    update_mock.assert_called_once()
    assert updated["last_decrypted_date"]
    assert "last_decrypted_date" not in item


def test_save_last_decryption_time_noops_when_disabled(mocker: MockerFixture):
    update_target_prefix = "confidant.services.secretmanager.store."
    update_target = update_target_prefix + "update_secret_last_decrypted_date"
    update_mock = mocker.patch(
        update_target,
    )
    mocker.patch("confidant.settings.ENABLE_SAVE_LAST_DECRYPTION_TIME", False)

    item = {"id": "cred-1"}
    result = secretmanager._save_last_decryption_time(
        "tenant-a",
        "cred-1",
        item,
    )
    assert result == item
    update_mock.assert_not_called()


def test_sanitize_write_items_strips_empty_values():
    items = [
        {
            "Item": {
                "PK": "x",
                "SK": "y",
                "documentation": "",
                "metadata": {},
                "tags": [],
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
            cipher_version=2,
            metadata={},
            modified_by="user@example.com",
            documentation=None,
            tags=[],
            last_rotation_date=None,
            last_decrypted_date=None,
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
