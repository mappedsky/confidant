import base64
import logging
import re

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

from confidant import settings

logger = logging.getLogger(__name__)

NONCE_BYTES = 12
TAG_BYTES = 16
KEY_BYTES = 32
CURRENT_CIPHER_VERSION = 3


def aes_gcm_encrypt(key, plaintext):
    """
    Encrypt plaintext bytes with AES-256-GCM using a fresh 12-byte nonce.
    Returns a URL-safe base64 string of nonce || ciphertext || tag.
    """
    nonce = get_random_bytes(NONCE_BYTES)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    return base64.urlsafe_b64encode(nonce + ciphertext + tag).decode("utf-8")


def aes_gcm_decrypt(key, token):
    """
    Decrypt a URL-safe base64 string produced by aes_gcm_encrypt. Raises on
    tag mismatch.
    """
    blob = base64.urlsafe_b64decode(token.encode("utf-8"))
    nonce = blob[:NONCE_BYTES]
    tag = blob[-TAG_BYTES:]
    ciphertext = blob[NONCE_BYTES:-TAG_BYTES]
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    return cipher.decrypt_and_verify(ciphertext, tag)


class CipherManager:
    """
    Class for encrypting and decrypting strings.

    cipher = CipherManager(key)
    encrypted_text = cipher.encrypt('hello world')
    decrypted_text = cipher.decrypt(encrypted_text)
    """

    def __init__(self, key, version=CURRENT_CIPHER_VERSION):
        self.key = key
        self.version = version

    def encrypt(self, raw):
        # Disabled encryption is dangerous, so we don't use falsiness here.
        if settings.USE_ENCRYPTION is False:
            logger.warning(
                "Not using encryption in CipherManager.encrypt. If you are not"
                " running in a development or test environment, this should not"
                " be happening!"
            )
            return "DANGER_NOT_ENCRYPTED_{}".format(
                base64.b64encode(raw.encode("UTF-8")).decode("UTF-8"),
            )
        if self.version == CURRENT_CIPHER_VERSION:
            return aes_gcm_encrypt(self.key, raw.encode("utf-8"))
        else:
            raise CipherManagerError("Bad cipher version")

    def decrypt(self, enc):
        # Disabled encryption is dangerous, so we don't use falsiness here.
        if settings.USE_ENCRYPTION is False:
            logger.warning(
                "Not using encryption in CipherManager.decrypt. If you are not"
                " running in a development or test environment, this should not"
                " be happening!"
            )
            return base64.b64decode(re.sub(r"^DANGER_NOT_ENCRYPTED_", "", enc))
        if self.version == CURRENT_CIPHER_VERSION:
            return aes_gcm_decrypt(self.key, enc)
        else:
            raise CipherManagerError("Bad cipher version")


class CipherManagerError(Exception):
    pass
