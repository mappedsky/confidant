import base64
import json
import logging

import yaml

import confidant.clients
from confidant.lib import cryptolib
from confidant.services.ciphermanager import aes_gcm_decrypt
from confidant.services.ciphermanager import CURRENT_CIPHER_VERSION

logger = logging.getLogger(__name__)


class EncryptedSettings:

    def __init__(self, secret_string, kms_url):
        self.secret_names = []
        self.secret_defaults = {}
        self.secret_string = secret_string
        self.decrypted_secrets = None
        self.kms_url = kms_url

    def register(self, name, default):
        """
        Lazy setup things that we want to get if we have kms
        """
        if name not in self.secret_names:
            self.secret_names.append(name)
            self.secret_defaults[name] = default
        return self.get_secret(name)

    def registered(self, name):
        return name in self.secret_names

    def get_secret(self, name):
        if self.decrypted_secrets is None:
            self.decrypted_secrets = self._bootstrap(self.secret_string)
        return self.decrypted_secrets.get(name, self.secret_defaults.get(name))

    def get_all_secrets(self):
        secrets = {}
        for name in self.secret_names:
            secrets[name] = self.get_secret(name)
        return secrets

    def _bootstrap(self, secrets):
        """
        Decrypt secrets and return a dict of secrets. Uses KMS to decrypt.
        """
        if not secrets:
            logger.info("SECRETS_BOOTSTRAP not set, skipping bootstrapping.")
            return {}
        if secrets.startswith("file://"):
            try:
                with open(secrets[7:]) as f:
                    _secrets = json.load(f)
            except OSError:
                logger.error(
                    "Failed to load file specified in SECRETS_BOOTSTRAP.",
                )
                return {}
        else:
            _secrets = json.loads(secrets)
        cipher_version = _secrets.get("cipher_version")
        if cipher_version != CURRENT_CIPHER_VERSION:
            raise ValueError(
                "SECRETS_BOOTSTRAP cipher_version {} is not supported; "
                "expected {}. Regenerate the bootstrap blob with the "
                "current version of confidant-admin.".format(
                    cipher_version,
                    CURRENT_CIPHER_VERSION,
                )
            )
        client = confidant.clients.get_boto_client(
            "kms",
            endpoint_url=self.kms_url,
        )
        key = cryptolib.decrypt_datakey(
            base64.b64decode(_secrets["data_key"]),
            {"type": "bootstrap"},
            client=client,
        )
        decrypted_secrets = yaml.safe_load(
            aes_gcm_decrypt(key, _secrets["secrets"]),
        )
        logger.info("Loaded SECRETS_BOOTSTRAP.")
        return decrypted_secrets
