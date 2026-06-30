"""Pure read-only VOOGLII UI specification helpers."""

from __future__ import annotations

__all__ = [
    "build_ui_spec_snapshot",
    "ui_spec_text",
    "build_dashboard_prototype_snapshot",
    "dashboard_prototype_text",
]


def _text(value, default="нет данных"):
    text = str(value or "").strip()
    return text if text else default


def _status(value, default="требует проверки"):
    text = str(value or "").strip()
    return text if text else default


def _unique_list(items):
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


def build_ui_spec_snapshot():
    return {
        "product": "VOOGLII",
        "version": "1.0",
        "positioning": "операционная система управления бизнесом на маркетплейсах",
        "principles": [
            "каждый экран отвечает на вопросы: что происходит, почему это происходит, что делать дальше",
            "workspace-first navigation вместо перегруженного списка legacy-команд",
            "единая структура экранов для бизнеса, финансов, товаров, аналитики и системы",
            "read-only surfaces не меняют расчёты и не подменяют source of truth",
        ],
        "workspaces": [
            "Dashboard",
            "Business",
            "Finance",
            "Products",
            "Advertising",
            "Analytics",
            "AI",
            "System",
        ],
        "kpi_rules": [
            "сначала общий статус, затем ключевые KPI",
            "каждый KPI должен быть привязан к периоду",
            "официальные и операционные показатели должны быть явно разделены",
        ],
        "ai_rules": [
            "не давать рекомендацию без объяснения",
            "не скрывать уровень уверенности",
            "не выдавать операционные данные за официальные",
            "показывать источники данных",
        ],
        "navigation": [
            "/home",
            "/business",
            "/finance",
            "/products",
            "/analytics",
            "/system",
            "/ui spec",
            "/dashboard prototype",
        ],
        "design_foundation": {
            "brand": "VOOGLII",
            "colors": "approved",
            "typography": "Inter",
            "ui_kit": "approved",
        },
        "status": "READY",
    }


def ui_spec_text(snapshot):
    snapshot = dict(snapshot or {})
    lines = [
        f'{snapshot.get("product") or "VOOGLII"} UI SPECIFICATION v{snapshot.get("version") or "1.0"}',
        "",
        "Позиционирование:",
        f'{snapshot.get("product") or "VOOGLII"} — {snapshot.get("positioning") or "операционная система управления бизнесом на маркетплейсах"}.',
        "",
        "Главный принцип:",
        "Каждый экран отвечает на 3 вопроса:",
        "1. Что происходит?",
        "2. Почему это происходит?",
        "3. Что делать дальше?",
        "",
        "Workspace Architecture:",
    ]
    for item in snapshot.get("workspaces") or []:
        lines.append(f"- {item}")
    lines.extend([
        "",
        "Единая структура Workspace:",
        "1. Заголовок",
        "2. Период",
        "3. Общий статус",
        "4. Ключевые KPI",
        "5. AI-анализ",
        "6. Что сделать сегодня",
        "7. Риски",
        "8. Детальная аналитика",
        "9. Связанные разделы",
        "",
        "Правила AI:",
    ])
    for item in snapshot.get("ai_rules") or []:
        lines.append(f"- {item}")
    design = dict(snapshot.get("design_foundation") or {})
    lines.extend([
        "",
        "Design Foundation:",
        f'- Brand: {design.get("brand") or "VOOGLII"}',
        f'- Colors: {design.get("colors") or "approved"}',
        f'- Typography: {design.get("typography") or "Inter"}',
        f'- UI Kit: {design.get("ui_kit") or "approved"}',
    ])
    return "\n".join(lines)


def _section_snapshot(name, command, snapshot=None, fallback_status="ожидает подтверждения"):
    snapshot = dict(snapshot or {})
    status = _status(snapshot.get("status"), fallback_status)
    summary = (
        snapshot.get("summary")
        or snapshot.get("message")
        or snapshot.get("headline")
        or snapshot.get("status_text")
        or fallback_status
    )
    return {
        "name": name,
        "command": command,
        "status": status,
        "summary": _text(summary, fallback_status),
    }


def build_dashboard_prototype_snapshot(
    period=None,
    director_snapshot=None,
    business_snapshot=None,
    finance_snapshot=None,
    products_snapshot=None,
    ads_snapshot=None,
    ai_snapshot=None,
):
    business = _section_snapshot("Business", "/business", business_snapshot)
    finance = _section_snapshot("Finance", "/finance", finance_snapshot)
    products = _section_snapshot("Products", "/products", products_snapshot)
    advertising = _section_snapshot("Advertising", "/analytics", ads_snapshot)
    ai = _section_snapshot("AI", "/home", ai_snapshot or director_snapshot)
    system = _section_snapshot("System", "/system", director_snapshot)

    today_actions = _unique_list([
        (business_snapshot or {}).get("main_action"),
        (finance_snapshot or {}).get("main_action"),
        (products_snapshot or {}).get("main_action"),
        (ads_snapshot or {}).get("main_action"),
        (ai_snapshot or {}).get("main_action"),
        "нет данных" if not any((business_snapshot, finance_snapshot, products_snapshot, ads_snapshot, ai_snapshot, director_snapshot)) else None,
    ])[:3]
    if not today_actions:
        today_actions = ["нет данных", "требует проверки", "ожидает подтверждения"]

    risks = _unique_list([
        (business_snapshot or {}).get("main_risk"),
        (finance_snapshot or {}).get("main_risk"),
        (products_snapshot or {}).get("main_risk"),
        (ads_snapshot or {}).get("main_risk"),
        (ai_snapshot or {}).get("main_risk"),
        "требует проверки" if not any((business_snapshot, finance_snapshot, products_snapshot, ads_snapshot, ai_snapshot, director_snapshot)) else None,
    ])[:3]
    if not risks:
        risks = ["требует проверки", "ожидает подтверждения"]

    statuses = [
        str(section.get("status") or "").upper()
        for section in (business, finance, products, advertising, ai, system)
    ]
    if any(status in ("BLOCKED", "CRITICAL", "FORBIDDEN", "ERROR") for status in statuses):
        overall_status = "требует проверки"
    elif any(status in ("UNKNOWN", "WARNING", "RATE_LIMIT", "PARTIAL", "UNAVAILABLE") for status in statuses):
        overall_status = "ожидает подтверждения"
    else:
        overall_status = "готов"

    return {
        "product": "VOOGLII",
        "screen": "dashboard_prototype",
        "period": _text(period, "current_month"),
        "overall_status": overall_status,
        "sections": {
            "business": business,
            "finance": finance,
            "products": products,
            "advertising": advertising,
            "ai": ai,
            "system": system,
        },
        "today_actions": today_actions,
        "risks": risks,
        "navigation": ["/business", "/finance", "/products", "/analytics", "/system"],
        "status": "READY",
    }


def dashboard_prototype_text(snapshot):
    snapshot = dict(snapshot or {})
    sections = dict(snapshot.get("sections") or {})
    business = dict(sections.get("business") or {})
    finance = dict(sections.get("finance") or {})
    advertising = dict(sections.get("advertising") or {})
    products = dict(sections.get("products") or {})
    lines = [
        "VOOGLII DASHBOARD PROTOTYPE",
        "",
        "Период:",
        _text(snapshot.get("period"), "current_month"),
        "",
        "Общий статус:",
        _text(snapshot.get("overall_status"), "ожидает подтверждения"),
        "",
        "Сегодня:",
        f'- Продажи: {business.get("summary") or "нет данных"}',
        f'- Финансы: {finance.get("summary") or "нет данных"}',
        f'- Реклама: {advertising.get("summary") or "нет данных"}',
        f'- Товары: {products.get("summary") or "нет данных"}',
        "",
        "AI рекомендует:",
    ]
    actions = list(snapshot.get("today_actions") or [])
    for idx, item in enumerate(actions[:3], start=1):
        lines.append(f"{idx}. {item}")
    lines.extend(["", "Требует внимания:"])
    risks = list(snapshot.get("risks") or [])
    for idx, item in enumerate(risks[:3], start=1):
        lines.append(f"{idx}. {item}")
    lines.extend(["", "Workspace:"])
    for item in snapshot.get("navigation") or []:
        lines.append(f"- {item}")
    lines.extend([
        "",
        "Важно:",
        "Это прототип будущего интерфейса, текущие расчёты не изменяются.",
    ])
    return "\n".join(lines)
