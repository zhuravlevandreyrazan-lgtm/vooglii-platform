from pathlib import Path
import os
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from security.token_crypto import decrypt_token, encrypt_token, is_encrypted_token, validate_wb_token


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    os.environ["VOOGLII_TOKEN_ENCRYPTION_KEY"] = "test-encryption-key-1234567890-abcdef"
    raw = validate_wb_token("abcdefghijklmnopqrstuvwxyz123456")
    encrypted = encrypt_token(raw)
    _assert(is_encrypted_token(encrypted), "token should be stored in encrypted format")
    _assert(raw not in encrypted, "plaintext token must not appear inside encrypted payload")
    _assert(decrypt_token(encrypted) == raw, "encrypted token should decrypt back to original value")


def test_main():
    main()


if __name__ == "__main__":
    main()
    print("TOKEN CRYPTO OK", flush=True)
