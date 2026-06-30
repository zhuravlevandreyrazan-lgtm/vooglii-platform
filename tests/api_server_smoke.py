from pathlib import Path
import sys

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api_server import app


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def run_smoke():
    client = TestClient(app)

    health_response = client.get("/api/health")
    _assert(health_response.status_code == 200, "/api/health should return 200")
    health_payload = health_response.json()
    _assert(health_payload.get("product") == "VOOGLII", "/api/health product mismatch")
    _assert(health_payload.get("mode") == "read_only", "/api/health mode mismatch")

    command_center_response = client.get("/api/command-center")
    _assert(command_center_response.status_code == 200, "/api/command-center should return 200")
    command_center_payload = command_center_response.json()
    _assert(command_center_payload.get("product") == "VOOGLII", "/api/command-center product mismatch")
    _assert(command_center_payload.get("screen") == "command_center", "/api/command-center screen mismatch")
    for key in ("business_health", "executive_brief", "kpis", "workspaces"):
        _assert(key in command_center_payload, f"/api/command-center missing {key}")


if __name__ == "__main__":
    run_smoke()
    print("API SERVER SMOKE OK", flush=True)
