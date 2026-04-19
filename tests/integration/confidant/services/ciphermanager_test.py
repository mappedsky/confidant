import base64

import pytest
from Crypto.Random import get_random_bytes

from confidant.services import ciphermanager
from confidant.services.ciphermanager import aes_gcm_decrypt
from confidant.services.ciphermanager import aes_gcm_encrypt
from confidant.services.ciphermanager import CipherManager
from confidant.services.ciphermanager import CipherManagerError
from confidant.services.ciphermanager import CURRENT_CIPHER_VERSION
from confidant.services.ciphermanager import NONCE_BYTES
from confidant.services.ciphermanager import TAG_BYTES


def test_current_cipher_version_is_three():
    # Pinning this protects callers that read cipher_version from storage
    # from being silently bumped by an unrelated constant change.
    assert CURRENT_CIPHER_VERSION == 3


def test_aes_gcm_token_layout():
    key = get_random_bytes(32)
    token = aes_gcm_encrypt(key, b"hello world")

    raw = base64.urlsafe_b64decode(token.encode("utf-8"))

    # 12-byte nonce || ciphertext (len == plaintext for GCM) || 16-byte tag.
    assert len(raw) == NONCE_BYTES + len(b"hello world") + TAG_BYTES


def test_aes_gcm_round_trip_with_large_payload():
    key = get_random_bytes(32)
    payload = b"confidant-integration-" * 512

    token = aes_gcm_encrypt(key, payload)
    assert aes_gcm_decrypt(key, token) == payload


def test_cipher_manager_rejects_truncated_token():
    key = get_random_bytes(32)
    token = CipherManager(key).encrypt("testdata")

    # Drop the last byte of the base64 payload before decrypting. GCM must
    # fail authentication rather than return garbage plaintext.
    with pytest.raises((ValueError, CipherManagerError)):
        CipherManager(key).decrypt(token[:-1])


def test_cipher_manager_default_version_matches_constant():
    key = get_random_bytes(32)
    cipher = CipherManager(key)
    assert cipher.version == ciphermanager.CURRENT_CIPHER_VERSION
