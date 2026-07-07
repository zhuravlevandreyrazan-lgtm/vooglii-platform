from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from vooglii_wb_sync import token_provider


def test_explicit_token_bypasses_resolution():
    resolved = token_provider.resolve_sync_token(1, token="secret-token")
    assert resolved.status == "OK"
    assert resolved.source == "function_arg"
    assert resolved.token == "secret-token"


if __name__ == "__main__":
    test_explicit_token_bypasses_resolution()
    print("WB SYNC TOKEN PROVIDER OK", flush=True)
