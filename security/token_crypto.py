from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets


TOKEN_PREFIX = "enc:v1:"
_PBKDF2_ROUNDS = 200_000
_NONCE_SIZE = 16
_TAG_SIZE = 32
_KEY_SIZE = 64


def _app_env() -> str:
    return str(os.getenv("APP_ENV") or "development").strip().lower() or "development"


def _raw_key() -> str:
    return str(os.getenv("VOOGLII_TOKEN_ENCRYPTION_KEY") or "").strip()


def is_token_encryption_configured() -> bool:
    return len(_raw_key()) >= 32


def validate_token_encryption_configuration(require_in_production: bool = True) -> None:
    key = _raw_key()
    if require_in_production and _app_env() == "production" and len(key) < 32:
        raise RuntimeError(
            "VOOGLII_TOKEN_ENCRYPTION_KEY is required in production and must be at least 32 characters long."
        )


def is_encrypted_token(value: str | None) -> bool:
    return str(value or "").startswith(TOKEN_PREFIX)


def validate_wb_token(raw_token: str) -> str:
    token = str(raw_token or "").strip()
    if len(token) < 20 or any(ch.isspace() for ch in token):
        raise ValueError("WB API token format is invalid.")
    return token


def _derive_keys(salt: bytes) -> tuple[bytes, bytes]:
    master = _raw_key().encode("utf-8")
    if len(master) < 32:
        raise RuntimeError("VOOGLII_TOKEN_ENCRYPTION_KEY is not configured.")
    derived = hashlib.pbkdf2_hmac("sha256", master, salt, _PBKDF2_ROUNDS, dklen=_KEY_SIZE)
    return derived[:32], derived[32:]


def _keystream(enc_key: bytes, nonce: bytes, length: int) -> bytes:
    stream = bytearray()
    counter = 0
    while len(stream) < length:
        block = hmac.new(enc_key, nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest()
        stream.extend(block)
        counter += 1
    return bytes(stream[:length])


def _xor_bytes(left: bytes, right: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(left, right))


def encrypt_token(raw_token: str) -> str:
    token = validate_wb_token(raw_token)
    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(_NONCE_SIZE)
    enc_key, auth_key = _derive_keys(salt)
    plaintext = token.encode("utf-8")
    ciphertext = _xor_bytes(plaintext, _keystream(enc_key, nonce, len(plaintext)))
    tag = hmac.new(auth_key, nonce + ciphertext, hashlib.sha256).digest()
    payload = base64.urlsafe_b64encode(salt + nonce + ciphertext + tag).decode("ascii")
    return f"{TOKEN_PREFIX}{payload}"


def decrypt_token(encrypted_token: str) -> str:
    if not is_encrypted_token(encrypted_token):
        return validate_wb_token(encrypted_token)
    payload = str(encrypted_token)[len(TOKEN_PREFIX):]
    blob = base64.urlsafe_b64decode(payload.encode("ascii"))
    if len(blob) <= 16 + _NONCE_SIZE + _TAG_SIZE:
        raise ValueError("Encrypted token payload is invalid.")
    salt = blob[:16]
    nonce = blob[16:16 + _NONCE_SIZE]
    ciphertext = blob[16 + _NONCE_SIZE:-_TAG_SIZE]
    tag = blob[-_TAG_SIZE:]
    enc_key, auth_key = _derive_keys(salt)
    expected_tag = hmac.new(auth_key, nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected_tag):
        raise ValueError("Encrypted token integrity check failed.")
    plaintext = _xor_bytes(ciphertext, _keystream(enc_key, nonce, len(ciphertext)))
    return validate_wb_token(plaintext.decode("utf-8"))

