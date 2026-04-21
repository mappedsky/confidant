from pytest_mock.plugin import MockerFixture

from confidant.lib import cryptolib
from confidant.services import secretmanager


def _mock_envelope(mocker: MockerFixture):
    """
    Bypass real KMS by returning a mock datakey, but leave the cipher manager
    running real AES-256-GCM. Returns the datakey dict so tests can inspect it.
    """
    mock_key = cryptolib.create_mock_datakey()
    mocker.patch(
        "confidant.services.secretmanager.keymanager.create_datakey",
        return_value=mock_key,
    )
    mocker.patch(
        "confidant.services.secretmanager.keymanager.decrypt_datakey",
        return_value=mock_key["plaintext"],
    )
    return mock_key


def test_encrypt_decrypt_secret_pairs_round_trip(mocker: MockerFixture):
    _mock_envelope(mocker)
    plaintext_pairs = {"password": "hunter2", "api_key": "abcd-1234"}

    encrypted, data_key, cipher_version = secretmanager._encrypt_secret_pairs(
        "tenant-a",
        "cred-1",
        plaintext_pairs,
    )

    # New secrets are always written under the current cipher version.
    assert cipher_version == 3

    # On-disk encoding is a URL-safe base64 string, never the plaintext.
    assert isinstance(encrypted, str)
    assert "hunter2" not in encrypted
    assert "abcd-1234" not in encrypted

    item = {
        "id": "cred-1",
        "tenant_id": "tenant-a",
        "secret_pairs": encrypted,
        "data_key": data_key,
        "cipher_version": cipher_version,
    }

    assert secretmanager._decrypt_secret_pairs(item) == plaintext_pairs


def test_encrypt_secret_pairs_uses_fresh_nonce(mocker: MockerFixture):
    _mock_envelope(mocker)

    first, _, _ = secretmanager._encrypt_secret_pairs(
        "tenant-a",
        "cred-1",
        {"password": "hunter2"},
    )
    second, _, _ = secretmanager._encrypt_secret_pairs(
        "tenant-a",
        "cred-1",
        {"password": "hunter2"},
    )

    # Same input + same data key must still produce different ciphertext,
    # because AES-GCM uses a fresh random nonce each call.
    assert first != second


def test_decrypt_secret_pairs_rejects_old_cipher_version(
    mocker: MockerFixture,
):
    _mock_envelope(mocker)

    encrypted, data_key, _ = secretmanager._encrypt_secret_pairs(
        "tenant-a",
        "cred-1",
        {"password": "hunter2"},
    )

    # Reading an item tagged with the retired Fernet version must fail,
    # not silently fall back to an unauthenticated path.
    item = {
        "id": "cred-1",
        "tenant_id": "tenant-a",
        "secret_pairs": encrypted,
        "data_key": data_key,
        "cipher_version": 2,
    }

    import pytest

    from confidant.services.ciphermanager import CipherManagerError

    with pytest.raises(CipherManagerError):
        secretmanager._decrypt_secret_pairs(item)
