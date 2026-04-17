"""Encryption utilities for sensitive data (API keys, tokens)."""

import base64
import secrets

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.config import get_settings


def _derive_key(secret: str) -> bytes:
    """Derive a Fernet key from the app secret."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"kwgrowth-salt-v1",  # Static salt - key rotates via APP_SECRET_KEY
        iterations=100_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(secret.encode()))


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string value using Fernet (AES-128-CBC)."""
    settings = get_settings()
    f = Fernet(_derive_key(settings.app_secret_key))
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted string."""
    settings = get_settings()
    f = Fernet(_derive_key(settings.app_secret_key))
    return f.decrypt(ciphertext.encode()).decode()


def generate_api_key() -> tuple[str, str]:
    """
    Generate an API key.

    Returns (full_key, prefix) where:
    - full_key: displayed once to the user (e.g., "kwge_a1b2c3d4e5f6...")
    - prefix: first 8 chars for identification in logs
    """
    raw = secrets.token_urlsafe(32)
    full_key = f"kwge_{raw}"
    prefix = full_key[:12]
    return full_key, prefix
