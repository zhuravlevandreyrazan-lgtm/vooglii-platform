"""Pure read-only product readiness helpers."""

PRODUCT_READINESS_ALLOWED_STATUS = ("READY", "PARTIAL", "BLOCKED")

__all__ = [
    "PRODUCT_READINESS_ALLOWED_STATUS",
    "build_product_readiness_snapshot",
    "product_readiness_text",
]


def _text_list(items):
    result = []
    seen = set()
    for item in list(items or []):
        text = str(item or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def build_product_readiness_snapshot(
    finance_api_status=None,
    director_ready=None,
    advisor_v2_ready=None,
    financial_engine_ready=None,
    control_center_ready=None,
    structure_readiness_status=None,
    remaining_blockers=None,
    recommended_next_step=None,
):
    director_ready = bool(director_ready)
    advisor_v2_ready = bool(advisor_v2_ready)
    financial_engine_ready = bool(financial_engine_ready)
    blockers = _text_list(remaining_blockers)

    if director_ready and advisor_v2_ready and financial_engine_ready and not blockers:
        product_status = "READY"
    elif director_ready:
        product_status = "PARTIAL"
    else:
        product_status = "BLOCKED"

    if not recommended_next_step:
        recommended_next_step = (
            "After Finance API is available, validate May 2026 against Gold Standard and migrate Profit Audit / Money Flow."
            if not financial_engine_ready
            else "Keep Director as the primary entrypoint and continue gradual migration of deep diagnostics."
        )

    return {
        "product_status": product_status,
        "primary_entrypoint": "/director",
        "finance_api_status": str(finance_api_status or "UNKNOWN"),
        "director_ready": director_ready,
        "advisor_v2_ready": advisor_v2_ready,
        "financial_engine_ready": financial_engine_ready,
        "control_center_ready": bool(control_center_ready),
        "structure_readiness_status": str(structure_readiness_status or "UNKNOWN"),
        "remaining_blockers": blockers,
        "recommended_next_step": str(recommended_next_step),
    }


def product_readiness_text(snapshot):
    snapshot = dict(snapshot or {})
    ready_items = []
    if snapshot.get("director_ready"):
        ready_items.append("Director")
    ready_items.extend(["KPI", "CFO Insights", "Decision Engine"])
    if snapshot.get("advisor_v2_ready"):
        ready_items.append("Advisor v2")

    blocked_items = list(snapshot.get("remaining_blockers") or [])

    lines = [
        "PRODUCT READINESS",
        "",
        f'Primary entrypoint: {snapshot.get("primary_entrypoint") or "/director"}',
        f'Status: {snapshot.get("product_status") or "PARTIAL"}',
        f'Control Center: {"READY" if snapshot.get("control_center_ready") else "PENDING"}',
        f'Structure readiness: {snapshot.get("structure_readiness_status") or "UNKNOWN"}',
        "",
        "Ready:",
    ]
    for item in ready_items:
        lines.append(f"- {item}")

    lines.extend(["", "Blocked:"])
    if blocked_items:
        for item in blocked_items:
            lines.append(f"- {item}")
    else:
        lines.append("- No critical blockers.")

    lines.extend([
        "",
        "Next step:",
        str(snapshot.get("recommended_next_step") or "-"),
    ])
    return "\n".join(lines)
