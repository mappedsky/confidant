import pytest

TEST_CERTIFICATE = \
    b'-----BEGIN CERTIFICATE-----\n' \
    b'MIIDoDCCAogCCQDqKOyH38qgKDANBgkqhkiG9w0BAQsFADCBkTELMAkGA1UEBhMC\n' \
    b'VVMxCzAJBgNVBAgMAkNBMRYwFAYDVQQHDA1UZXN0IExvY2FsaXR5MRIwEAYDVQQK\n' \
    b'DAlMeWZ0IFRlc3QxEjAQBgNVBAsMCVRlc3QgVW5pdDENMAsGA1UEAwwEdGVzdDEm\n' \
    b'MCQGCSqGSIb3DQEJARYXdGVzdC1zb21ldGhpbmdAbHlmdC5jb20wHhcNMjIxMDA3\n' \
    b'MjMxNTM5WhcNMjMxMDA3MjMxNTM5WjCBkTELMAkGA1UEBhMCVVMxCzAJBgNVBAgM\n' \
    b'AkNBMRYwFAYDVQQHDA1UZXN0IExvY2FsaXR5MRIwEAYDVQQKDAlMeWZ0IFRlc3Qx\n' \
    b'EjAQBgNVBAsMCVRlc3QgVW5pdDENMAsGA1UEAwwEdGVzdDEmMCQGCSqGSIb3DQEJ\n' \
    b'ARYXdGVzdC1zb21ldGhpbmdAbHlmdC5jb20wggEiMA0GCSqGSIb3DQEBAQUAA4IB\n' \
    b'DwAwggEKAoIBAQDUu1TaFSVNJELfYiV++1ZDAbrQ/flor64XOwK9RItzYqvnEUU1\n' \
    b'+aHw4QvDNyKJsyH7/uqv42vDZiCiAH6T1RVLD30AdIswOQpVSsQcPEXcJfkIJ3ZQ\n' \
    b'SWpuTVMbvJukrWK9ScPFkUyBC7FpkZ/RJ6pwiE2nVHjcrysAmK2/KB1Hk/NmO+fw\n' \
    b'evIcYXwrxNLm9k6XM5xyJcl7ZK3GInZbuEcH4NdRYnAo7dCLtuwRFUW4fgSRUjjx\n' \
    b'FXGJLd830iDgHzM0VyTq77gzKpn5VEZbIvDWgc8oxKHsrJKbyv3UGeC0q04K2EQR\n' \
    b'6tq71gbS/hv9QCxmR6ygNqq8bz0dsmZXeeYxAgMBAAEwDQYJKoZIhvcNAQELBQAD\n' \
    b'ggEBAIPQnGGAlwbK+f4V7SUUjXnsO7oVlMtTO7JWAk+g8W9colUeMDHW/Ygcwu3e\n' \
    b'OlX5NSEV1wcQxuqyNWbEgrsZourePdVWujc/9qSVfaU/BjOj2CLylAf6ZNj/XpL/\n' \
    b'PNCSCLM40cbhw/SeiNZ9WxkuuHiC32QxmR4kyvvXcHEGqVA2cOVAvncstW4gGowi\n' \
    b'ObNYddXOmoOf8d5oHcO5vlhYyfbmShuq1PLygzUhG2jS+5aX9gmDtv+LtVGdXXWV\n' \
    b'zSCh3+H4NSUWs3P1pKDFIUT3jGLQ3UavIS5KCizfBUbltx6LBSgmBbHf89RsKBbT\n' \
    b'rxaukysD4sNgVHKptTq0fJ+2CjM=\n' \
    b'-----END CERTIFICATE-----\n'


@pytest.fixture(autouse=True)
def encrypted_settings_mock(mocker):
    mocker.patch('confidant.settings.encrypted_settings.secret_string', {})
    mocker.patch(
        'confidant.settings.encrypted_settings.decrypted_secrets',
        {'SESSION_SECRET': 'TEST_KEY'},
    )


@pytest.fixture
def test_certificate():
    return TEST_CERTIFICATE
