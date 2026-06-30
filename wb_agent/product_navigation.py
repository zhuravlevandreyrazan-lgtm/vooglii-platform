"""Pure read-only product navigation helpers."""

PRODUCT_NAVIGATION_ALLOWED_MODES = ("USER", "ADVANCED", "DEVELOPER")

__all__ = [
    "PRODUCT_NAVIGATION_ALLOWED_MODES",
    "build_product_navigation_snapshot",
    "product_navigation_text",
]


def build_product_navigation_snapshot(user_mode="user", period=None):
    normalized_mode = str(user_mode or "user").strip().upper()
    if normalized_mode not in PRODUCT_NAVIGATION_ALLOWED_MODES:
        normalized_mode = "USER"

    primary_sections = [
        {"name": "Home", "command": "/home", "description": "main executive summary"},
        {"name": "Business", "command": "/business", "description": "business health, risks, recommendations"},
        {"name": "Finance", "command": "/finance", "description": "money, profit, payouts, reconciliation"},
        {"name": "Products", "command": "/products", "description": "sku, costs, stock, assortment"},
        {"name": "Analytics", "command": "/analytics", "description": "reports, ads, trends, diagnostics"},
        {"name": "System", "command": "/system", "description": "agent status and diagnostic tools"},
        {"name": "Help", "command": "/help", "description": "help and navigation modes"},
    ]

    hidden_legacy_commands = [
        "/director",
        "/advisor v2",
        "/decision",
        "/cfo insights",
        "/kpi",
        "/financial engine",
        "/business metrics",
        "/udl",
        "/payment reconciliation",
        "/profit audit",
        "/money flow",
        "/money sku",
        "/report",
        "/report ceo",
        "/dashboard",
        "/advert",
        "/orders",
        "/funnel",
        "/stocks",
        "/forecast",
        "/replenishment",
        "/sku registry",
    ]
    developer_commands = [
        "/ui spec",
        "/dashboard prototype",
        "/telegram identity",
        "/financial engine",
        "/business metrics",
        "/udl",
        "/command audit",
        "/migration readiness",
        "/performance",
        "/rc status",
        "/control center",
        "/structure readiness",
        "/period",
        "/sku registry",
        "/ads ...",
        "/sales ...",
    ]
    aliases = {
        "/home": ["/director current_month"],
        "/business": ["/director", "/advisor v2", "/decision", "/cfo insights", "/kpi", "/business metrics"],
        "/finance": ["/financial engine", "/money flow", "/profit audit", "/payment reconciliation", "/finance api status"],
        "/products": ["/sku registry", "/stocks", "/forecast", "/replenishment", "/money sku"],
        "/analytics": ["/dashboard", "/report ceo", "/report month", "/advert month", "/orders", "/funnel"],
        "/system": ["/control center", "/system audit", "/performance", "/rc status", "/product readiness", "/structure readiness"],
    }

    warnings = []
    if period:
        warnings.append(f"Current navigation context period: {period}")

    return {
        "status": "OK",
        "mode": normalized_mode,
        "primary_sections": primary_sections,
        "hidden_legacy_commands": hidden_legacy_commands,
        "developer_commands": developer_commands,
        "aliases": aliases,
        "recommended_entrypoint": "/home",
        "warnings": warnings,
    }


def product_navigation_text(snapshot):
    snapshot = dict(snapshot or {})
    lines = [
        "PRODUCT NAVIGATION",
        "",
        f'mode: {snapshot.get("mode") or "USER"}',
        f'recommended_entrypoint: {snapshot.get("recommended_entrypoint") or "/home"}',
        "",
        "Primary Sections:",
    ]
    for item in snapshot.get("primary_sections") or []:
        lines.append(f'- {item.get("command") or "-"}: {item.get("description") or "-"}')
    lines.extend(["", "Developer Commands:"])
    for item in snapshot.get("developer_commands") or []:
        lines.append(f"- {item}")
    return "\n".join(lines)
