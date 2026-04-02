from confidant.models.credential import Credential
from confidant.services import credentialmanager
from pynamodb.exceptions import DoesNotExist
import base64

from pytest_mock.plugin import MockerFixture


def test_get_revision_ids_for_credential():
    credential = Credential(
        id='1234',
        revision=3,
        name='test',
        enabled=True,
    )
    assert credentialmanager.get_revision_ids_for_credential(credential) == [
        '1234-1',
        '1234-2',
        '1234-3',
    ]


def test_get_latest_credential_revision(mocker: MockerFixture):
    get = mocker.patch(
        'confidant.models.credential.Credential.get'
    )
    get.side_effect = DoesNotExist()
    res = credentialmanager.get_latest_credential_revision('123', 1)
    assert res == 2


def test_check_credential_pair_values(mocker: MockerFixture):
    cred_pairs_success = {
        'A': '1'
    }
    cred_pairs_fail = {
        'A': ['1', '2', '3']
    }
    cred_pair_fail_2 = {
        'A': {'1': '2'}
    }
    cred_pair_fail_3 = {
        'A A': {'1': '2'}
    }
    result = credentialmanager.check_credential_pair_values(cred_pairs_fail)
    assert result[0] is False
    result = credentialmanager.check_credential_pair_values(cred_pair_fail_2)
    assert result[0] is False
    result = credentialmanager.check_credential_pair_values(cred_pair_fail_3)
    assert result[0] is False
    result = credentialmanager.check_credential_pair_values(cred_pairs_success)
    assert result[0] is True


def test_lowercase_credential_pairs():
    test = {
        'A': '123',
        'B': '345',
        'C': '678'
    }

    expected = {
        'a': '123',
        'b': '345',
        'c': '678'
    }
    res = credentialmanager.lowercase_credential_pairs(test)
    assert res == expected


def test_encrypt_credential_pairs_encodes_data_key(mocker: MockerFixture):
    mocker.patch(
        'confidant.services.keymanager.create_datakey',
        return_value={'plaintext': b'plaintext', 'ciphertext': b'ciphertext'},
    )
    cipher_mock = mocker.patch(
        'confidant.services.credentialmanager.CipherManager',
    )
    cipher_mock.return_value.encrypt.return_value = 'encrypted-pairs'
    _, data_key, _ = credentialmanager._encrypt_credential_pairs(
        'tenant-a',
        'cred-1',
        {'a': 'b'},
    )
    assert data_key == base64.b64encode(b'ciphertext').decode('UTF-8')


def test_save_last_decryption_time_updates_store_and_item(mocker: MockerFixture):
    update_mock = mocker.patch(
        'confidant.services.credentialmanager.store.update_credential_last_decrypted_date',
    )
    mocker.patch('confidant.settings.ENABLE_SAVE_LAST_DECRYPTION_TIME', True)

    item = {'id': 'cred-1', 'tenant_id': 'tenant-a'}
    updated = credentialmanager._save_last_decryption_time(
        'tenant-a',
        'cred-1',
        item,
    )

    update_mock.assert_called_once()
    assert updated['last_decrypted_date']
    assert 'last_decrypted_date' not in item


def test_save_last_decryption_time_noops_when_disabled(mocker: MockerFixture):
    update_mock = mocker.patch(
        'confidant.services.credentialmanager.store.update_credential_last_decrypted_date',
    )
    mocker.patch('confidant.settings.ENABLE_SAVE_LAST_DECRYPTION_TIME', False)

    item = {'id': 'cred-1'}
    assert credentialmanager._save_last_decryption_time('tenant-a', 'cred-1', item) == item
    update_mock.assert_not_called()


def test_sanitize_write_items_strips_empty_values():
    items = [
        {
            'Item': {
                'PK': 'x',
                'SK': 'y',
                'documentation': '',
                'metadata': {},
                'tags': [],
                'value': 'ok',
            },
            'ConditionExpression': 'attribute_not_exists(PK)',
        }
    ]

    sanitized = credentialmanager._sanitize_write_items(items)

    assert sanitized == [
        {
            'Item': {
                'PK': 'x',
                'SK': 'y',
                'value': 'ok',
            },
            'ConditionExpression': 'attribute_not_exists(PK)',
        }
    ]
