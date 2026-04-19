from pytest_mock.plugin import MockerFixture

from confidant.services import keymanager


def test_create_datakey_mocked(mocker: MockerFixture):
    mock_key = b"\x00" * 32
    mock_datakey = mocker.patch(
        "confidant.services.keymanager.cryptolib.create_mock_datakey",
        return_value={"ciphertext": mock_key, "plaintext": mock_key},
    )
    mocker.patch("confidant.services.keymanager.settings.USE_ENCRYPTION", False)

    ret = keymanager.create_datakey({})

    assert mock_datakey.called is True

    # Assert that we got a dict returned where the ciphertext and plaintext
    # keys are equal
    assert ret["ciphertext"] == ret["plaintext"]

    # Assert ciphertext is the mocked key
    assert ret["ciphertext"] == mock_key


def test_decrypt_datakey_mocked(mocker: MockerFixture):
    mocker.patch("confidant.services.keymanager.settings.USE_ENCRYPTION", False)
    ret = keymanager.decrypt_datakey(b"\x00" * 32)

    # Ensure we get the same value out that we sent in.
    assert ret == b"\x00" * 32


def test_create_datakey_with_encryption(mocker: MockerFixture):
    cd_mock = mocker.patch(
        "confidant.services.keymanager.cryptolib.create_datakey",
    )
    cmd_mock = mocker.patch(
        "confidant.services.keymanager.cryptolib.create_mock_datakey"
    )
    mocker.patch("confidant.services.keymanager.settings.USE_ENCRYPTION", True)
    context = {"from": "confidant-development", "to": "confidant-development"}
    keymanager.create_datakey(context)

    # Assert that create_datakey was called and create_mock_datakey was
    # not called.
    assert cd_mock.called is True
    assert cmd_mock.called is False


def test_decrypt_datakey_with_encryption(mocker: MockerFixture):
    dd_mock = mocker.patch(
        "confidant.services.keymanager.cryptolib.decrypt_datakey",
    )
    dmd_mock = mocker.patch(
        "confidant.services.keymanager.cryptolib.decrypt_mock_datakey"
    )

    mocker.patch("confidant.services.keymanager.settings.USE_ENCRYPTION", True)
    context = {"from": "confidant-development", "to": "confidant-development"}
    keymanager.decrypt_datakey(b"encrypted", context)

    # Assert that decrypt_datakey was called and decrypt_mock_datakey was
    # not called.
    assert dd_mock.called is True
    assert dmd_mock.called is False
