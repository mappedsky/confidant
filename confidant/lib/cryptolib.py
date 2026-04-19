from Crypto.Random import get_random_bytes


def decrypt_mock_datakey(data_key):
    """
    Mock decryption meant to be used for testing or development. Simply returns
    the provided data_key.
    """
    return data_key


def decrypt_datakey(data_key, encryption_context=None, client=None):
    """
    Decrypt a datakey.
    """
    return client.decrypt(
        CiphertextBlob=data_key, EncryptionContext=encryption_context
    )["Plaintext"]


def create_mock_datakey():
    """
    Mock encryption meant to be used for testing or development. Returns a
    generated data key, but the encrypted version of the key is simply the
    unencrypted version. If this is called for anything other than testing
    or development purposes, it will cause unencrypted keys to be stored along
    with the encrypted content, rending the encryption worthless.
    """
    key = get_random_bytes(32)
    return {"ciphertext": key, "plaintext": key}


def create_datakey(encryption_context, keyid, client=None):
    """
    Create a datakey from KMS. Returns 32 raw bytes of plaintext key suitable
    for AES-256-GCM, and the KMS-encrypted ciphertext of those same 32 bytes.
    """
    key = client.generate_random(NumberOfBytes=32)["Plaintext"]
    response = client.encrypt(
        KeyId=f"{keyid}",
        Plaintext=key,
        EncryptionContext=encryption_context,
    )
    return {"ciphertext": response["CiphertextBlob"], "plaintext": key}
