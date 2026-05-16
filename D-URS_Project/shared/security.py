# shared/security.py
# Helper functions for SHA-256 hashing and token generation

import hashlib
import secrets


def hash_sha256(data: str) -> str:
    """Return the SHA-256 hex digest of the given string."""
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def hash_data(data: str) -> str:
    """Hash a string using SHA-256. Used for password hashing and File GUIDs."""
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def generate_token() -> str:
    """Generate a secure random session token."""
    return secrets.token_hex(16)


def hash_file(file_path: str) -> str:
    """Return the SHA-256 hex digest of a file's contents."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()
