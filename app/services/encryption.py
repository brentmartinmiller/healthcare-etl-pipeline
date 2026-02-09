"""
Application-layer encryption for PHI/PII fields.

Demonstrates:
- Symmetric encryption (AES-GCM via Fernet) for data at rest
- Key management awareness (key from env, not hardcoded)
- Encrypt/decrypt interface for use in ETL transforms
"""

import base64
import os

from cryptography.fernet import Fernet


class EncryptionService:
    """Wraps Fernet symmetric encryption for PHI fields."""

    def __init__(self, key: str | None = None):
        raw_key = key or os.getenv("PHI_ENCRYPTION_KEY", "")
        if raw_key:
            self._fernet = Fernet(raw_key.encode() if isinstance(raw_key, str) else raw_key)
        else:
            # Generate a key for development – in production this MUST come from
            # a secrets manager (AWS Secrets Manager, Vault, etc.)
            generated = Fernet.generate_key()
            self._fernet = Fernet(generated)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string and return base64-encoded ciphertext."""
        if not plaintext:
            return ""
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt base64-encoded ciphertext back to plaintext."""
        if not ciphertext:
            return ""
        return self._fernet.decrypt(ciphertext.encode()).decode()
