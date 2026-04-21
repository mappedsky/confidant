import base64

import pytest
from Crypto.Random import get_random_bytes

from confidant.services.ciphermanager import CipherManager, CipherManagerError


def test_cipher_version_3():
    key = get_random_bytes(32)
    cipher = CipherManager(key, 3)
    ciphertext = cipher.encrypt("testdata")

    # Assert we're getting back some form of altered data
    assert ciphertext != "testdata"

    cipher = CipherManager(key, 3)
    plaintext = cipher.decrypt(ciphertext).decode("UTF-8")

    # Assert that decrypting using a new cipher object with the same key
    # and version give back the same plaintext.
    assert plaintext == "testdata"


def test_cipher_version_3_uses_fresh_nonce():
    key = get_random_bytes(32)
    cipher = CipherManager(key, 3)

    a = cipher.encrypt("testdata")
    b = cipher.encrypt("testdata")

    # Different nonces each call => different ciphertexts for the same input.
    assert a != b


def test_cipher_version_1():
    key = get_random_bytes(32)
    cipher = CipherManager(key, 1)
    with pytest.raises(CipherManagerError):
        cipher.encrypt("testdata")
    with pytest.raises(CipherManagerError):
        cipher.decrypt("random_text")


def test_cipher_version_2_rejected():
    key = get_random_bytes(32)
    cipher = CipherManager(key, 2)
    with pytest.raises(CipherManagerError):
        cipher.encrypt("testdata")
    with pytest.raises(CipherManagerError):
        cipher.decrypt("random_text")


def test_tampered_ciphertext_fails():
    key = get_random_bytes(32)
    cipher = CipherManager(key, 3)
    token = cipher.encrypt("testdata")

    # Flip a byte in the middle of the blob.
    blob = bytearray(base64.urlsafe_b64decode(token.encode("utf-8")))
    blob[len(blob) // 2] ^= 0xFF
    tampered = base64.urlsafe_b64encode(bytes(blob)).decode("utf-8")

    with pytest.raises(ValueError):
        cipher.decrypt(tampered)


def test_wrong_key_fails():
    key_a = get_random_bytes(32)
    key_b = get_random_bytes(32)
    token = CipherManager(key_a, 3).encrypt("testdata")

    with pytest.raises(ValueError):
        CipherManager(key_b, 3).decrypt(token)
