from pathlib import Path
import importlib
import os
import sys
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    with tempfile.TemporaryDirectory() as tmp_dir:
        os.environ["DB_DIR"] = tmp_dir
        os.environ["VOOGLII_TOKEN_ENCRYPTION_KEY"] = "test-encryption-key-1234567890-abcdef"
        os.environ["ADMIN_IDS"] = "9001"

        import config
        import db_manager
        import user_manager
        import security.permissions as permissions

        importlib.reload(config)
        importlib.reload(db_manager)
        importlib.reload(user_manager)
        importlib.reload(permissions)

        user_manager.ensure_user(100, "viewer_user")
        user_manager.set_role(100, "viewer")
        user_manager.ensure_user(101, "manager_user")
        user_manager.set_role(101, "manager")

        _assert(permissions.has_permission(100, "customer.dashboard"), "viewer should see dashboard")
        _assert(not permissions.has_permission(100, "command.admin"), "viewer must not access admin commands")
        _assert(permissions.has_permission(101, "customer.update"), "manager should be able to update")
        _assert(permissions.is_admin(9001), "bootstrap ADMIN_IDS should still work")


def test_main():
    main()


if __name__ == "__main__":
    main()
    print("PERMISSIONS OK", flush=True)
