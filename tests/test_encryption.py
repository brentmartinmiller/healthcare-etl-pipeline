"""Tests for the PHI encryption service."""

from app.services.encryption import EncryptionService


def test_encrypt_decrypt_roundtrip():
    svc = EncryptionService()
    original = "John Doe, DOB 1985-03-22, SSN 123-45-6789"
    encrypted = svc.encrypt(original)

    assert encrypted != original  # not stored in plaintext
    assert svc.decrypt(encrypted) == original


def test_empty_string_passthrough():
    svc = EncryptionService()
    assert svc.encrypt("") == ""
    assert svc.decrypt("") == ""
