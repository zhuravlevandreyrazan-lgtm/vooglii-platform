BRAND_NAME = "VOOGLII"
PRODUCT_NAME = "VOOGLII Terminal"


def divider() -> str:
    return "━━━━━━━━━━━━━━"


def title(icon: str, text: str) -> str:
    return f"{icon} {text}".strip()


def section(text: str) -> str:
    return str(text or "").strip()


def bullet(text: str) -> str:
    return f"- {str(text or '').strip()}"


def status_dot(status: str) -> str:
    value = str(status or "").strip().upper()
    if value in ("OK", "READY", "AVAILABLE", "SUCCESS", "ACTIVE", "HIGH", "CONNECTED"):
        return "🟢"
    if value in ("WARNING", "PARTIAL", "LIMITED", "MEDIUM", "PENDING"):
        return "🟡"
    if value in ("ERROR", "FAILED", "LOW", "CRITICAL", "DISCONNECTED", "BLOCKED", "FORBIDDEN"):
        return "🔴"
    return "⚪"
