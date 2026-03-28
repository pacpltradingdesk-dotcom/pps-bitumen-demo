"""
vault_engine.py — Encrypted Local Vault for PPS Anantam
=========================================================

Fernet symmetric encryption for all credentials and API keys.
Key derived from machine-specific seed (hostname + username + salt file).

Priority chain for secrets:
  1. Environment variable (if configured)
  2. Encrypted vault file (vault.enc)
  3. Empty string (graceful fallback)

Auto-migrates legacy base64-encoded credentials on first access.
"""

import os
import json
import hashlib
import base64
import getpass
import socket
import logging
from pathlib import Path

LOG = logging.getLogger("vault_engine")
BASE = Path(__file__).resolve().parent
VAULT_FILE = BASE / "vault.enc"
SALT_FILE = BASE / ".vault_salt"

# ---------------------------------------------------------------------------
# Key derivation
# ---------------------------------------------------------------------------

_HAS_CRYPTOGRAPHY = False
try:
    from cryptography.fernet import Fernet
    _HAS_CRYPTOGRAPHY = True
except ImportError:
    pass


def _get_or_create_salt() -> bytes:
    """Get or create a persistent random salt."""
    if SALT_FILE.exists():
        return SALT_FILE.read_bytes()
    salt = os.urandom(32)
    try:
        SALT_FILE.write_bytes(salt)
    except OSError as e:
        LOG.warning("Cannot write salt file: %s", e)
    return salt


def _derive_key() -> bytes:
    """Derive Fernet key from machine identity + salt."""
    salt = _get_or_create_salt()
    machine_id = f"{socket.gethostname()}:{getpass.getuser()}".encode()
    raw = hashlib.pbkdf2_hmac("sha256", machine_id, salt, 100_000)
    return base64.urlsafe_b64encode(raw)


def _get_fernet():
    """Get Fernet cipher instance. Raises ImportError if cryptography missing."""
    if not _HAS_CRYPTOGRAPHY:
        raise ImportError("cryptography package not installed")
    return Fernet(_derive_key())


# ---------------------------------------------------------------------------
# Encrypt / Decrypt
# ---------------------------------------------------------------------------

def encrypt_value(plaintext: str) -> str:
    """Encrypt a string, return Fernet token as string."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_value(token: str) -> str:
    """Decrypt a Fernet token back to plaintext."""
    f = _get_fernet()
    return f.decrypt(token.encode("utf-8")).decode("utf-8")


# ---------------------------------------------------------------------------
# Vault file (stores all secrets as a single encrypted JSON blob)
# ---------------------------------------------------------------------------

def _load_vault() -> dict:
    """Load and decrypt the vault file. Returns empty dict on failure."""
    if not VAULT_FILE.exists():
        return {}
    try:
        f = _get_fernet()
        raw = VAULT_FILE.read_bytes()
        return json.loads(f.decrypt(raw).decode("utf-8"))
    except Exception:
        return {}


def _save_vault(data: dict):
    """Encrypt and save the vault file."""
    f = _get_fernet()
    raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
    VAULT_FILE.write_bytes(f.encrypt(raw))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_secret(key: str, env_var: str = "") -> str:
    """
    Retrieve a secret.

    Priority:
      1. Environment variable (if env_var provided and set)
      2. Encrypted vault
      3. Empty string

    Parameters
    ----------
    key : str
        Vault key name (e.g. "api_key_eia", "email_password").
    env_var : str
        Optional environment variable name to check first.
    """
    # Priority 1: Environment variable
    if env_var:
        val = os.environ.get(env_var, "").strip()
        if val:
            return val
    # Priority 2: Vault
    if not _HAS_CRYPTOGRAPHY:
        return ""
    vault = _load_vault()
    encrypted = vault.get(key, "")
    if encrypted:
        try:
            return decrypt_value(encrypted)
        except Exception:
            return ""
    return ""


def set_secret(key: str, plaintext: str):
    """Store a secret in the encrypted vault."""
    if not _HAS_CRYPTOGRAPHY:
        LOG.warning("Cannot store secret: cryptography package not installed")
        return
    vault = _load_vault()
    vault[key] = encrypt_value(plaintext)
    _save_vault(vault)


def delete_secret(key: str):
    """Remove a secret from the vault."""
    if not _HAS_CRYPTOGRAPHY:
        return
    vault = _load_vault()
    if key in vault:
        del vault[key]
        _save_vault(vault)


def list_keys() -> list:
    """Return all key names stored in the vault (not values)."""
    if not _HAS_CRYPTOGRAPHY:
        return []
    return list(_load_vault().keys())


# ---------------------------------------------------------------------------
# Migration helpers
# ---------------------------------------------------------------------------

def is_base64_plain(value: str) -> bool:
    """Detect if a value is likely base64-encoded plaintext (legacy format)."""
    if not value or len(value) < 4:
        return False
    try:
        decoded = base64.b64decode(value).decode("utf-8")
        return decoded.isprintable() and len(decoded) > 0
    except Exception:
        return False


def migrate_base64_to_vault(key: str, b64_value: str) -> bool:
    """Auto-migrate a base64 encoded value to Fernet encryption."""
    if not _HAS_CRYPTOGRAPHY:
        return False
    try:
        plaintext = base64.b64decode(b64_value).decode("utf-8")
        set_secret(key, plaintext)
        return True
    except Exception:
        return False


def mask_secret(value: str, show_last: int = 4) -> str:
    """Return masked version for UI display: ****last4."""
    if not value or len(value) <= show_last:
        return "****"
    return "*" * (len(value) - show_last) + value[-show_last:]


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def get_vault_status() -> dict:
    """Return vault health status for system dashboard."""
    return {
        "cryptography_available": _HAS_CRYPTOGRAPHY,
        "vault_exists": VAULT_FILE.exists(),
        "salt_exists": SALT_FILE.exists(),
        "keys_stored": len(list_keys()),
    }
