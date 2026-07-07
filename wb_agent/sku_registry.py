"""Read-only SKU registry and reference cost helpers."""

from wb_agent.formatting import money

SKU_REGISTRY_STATUS_VALUES = ("OK", "PARTIAL", "EMPTY")

_SKU_COST_REFERENCE = {
    "Kryshki10_82mm": 82.0,
    "PM-2": 760.0,
    "Kryshki10_58mm": 35.0,
    "Plenka15*3_60мкм": 271.0,
    "Plenka10*3_80мкм": 238.0,
    "Plenka10*3": 184.0,
    "meshki10": 10.0,
    "Gorshki_12": 166.0,
    "Lozhka_plastic_золото": 100.0,
    "Lozhka_plastic_черный": 100.0,
    "Lozhka_plastic_синий": 100.0,
    "Lozhka_Derevo_черн": 100.0,
    "Lozhka_Derevo_коричн": 100.0,
    "OZ-1": 900.0,
}

__all__ = [
    "SKU_REGISTRY_STATUS_VALUES",
    "get_sku_cost",
    "sku_cost_reference_data",
    "build_sku_registry_snapshot",
    "sku_registry_text",
]


def sku_cost_reference_data():
    return dict(_SKU_COST_REFERENCE)


def get_sku_cost(supplier_article, sale_date=None):
    _ = sale_date
    article = str(supplier_article or "").strip()
    if not article:
        return None
    value = _SKU_COST_REFERENCE.get(article)
    return None if value is None else round(float(value), 2)


def _normalize_sku_list(items):
    result = []
    seen = set()
    for item in list(items or []):
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def build_sku_registry_snapshot(sales_skus=None, finance_skus=None, catalog_rows=None):
    reference = sku_cost_reference_data()
    for item in list(catalog_rows or []):
        article = str((item or {}).get("supplier_article") or "").strip()
        if not article:
            continue
        unit_cost = (item or {}).get("cost_price")
        if unit_cost not in (None, ""):
            try:
                reference[article] = round(float(unit_cost), 2)
            except Exception:
                pass
    reference_keys = list(reference.keys())
    requested_skus = _normalize_sku_list(list(sales_skus or []) + list(finance_skus or []))

    if requested_skus:
        known_skus = [sku for sku in requested_skus if sku in reference]
        missing_skus = [sku for sku in requested_skus if sku not in reference]
        denominator = len(requested_skus)
    else:
        known_skus = list(reference_keys)
        missing_skus = []
        denominator = len(reference_keys)

    coverage_percent = round((len(known_skus) / denominator) * 100.0, 1) if denominator > 0 else 0.0
    if denominator <= 0:
        registry_status = "EMPTY"
    elif not missing_skus:
        registry_status = "OK"
    else:
        registry_status = "PARTIAL"

    row_source = requested_skus if requested_skus else reference_keys
    rows = []
    for sku in row_source:
        unit_cost = reference.get(sku)
        rows.append({
            "supplier_article": sku,
            "unit_cost": None if unit_cost is None else round(float(unit_cost), 2),
            "cost_status": "OK" if unit_cost is not None else "MISSING",
        })

    return {
        "total_reference_skus": int(len(reference_keys)),
        "known_skus": list(known_skus),
        "missing_skus": list(missing_skus),
        "coverage_percent": coverage_percent,
        "registry_status": registry_status,
        "rows": rows,
    }


def sku_registry_text(snapshot):
    snapshot = dict(snapshot or {})
    lines = [
        "SKU REGISTRY",
        "",
        f'total reference SKUs: {int(snapshot.get("total_reference_skus") or 0)}',
        f'known SKUs: {len(snapshot.get("known_skus") or [])}',
        f'missing SKUs: {len(snapshot.get("missing_skus") or [])}',
        f'coverage: {float(snapshot.get("coverage_percent") or 0):.1f}%',
        f'status: {snapshot.get("registry_status") or "EMPTY"}',
    ]
    missing = list(snapshot.get("missing_skus") or [])
    if missing:
        lines.extend([
            "",
            "Missing:",
            ", ".join(missing[:50]),
        ])
    else:
        lines.extend([
            "",
            "Missing:",
            "none",
        ])
    rows = list(snapshot.get("rows") or [])
    if rows:
        lines.extend(["", "Rows:"])
        for item in rows[:20]:
            if item.get("unit_cost") is None:
                lines.append(f'{item.get("supplier_article") or "-"} | cost: missing | status: {item.get("cost_status") or "MISSING"}')
            else:
                lines.append(f'{item.get("supplier_article") or "-"} | cost: {money(item.get("unit_cost") or 0)} | status: {item.get("cost_status") or "OK"}')
    return "\n".join(lines)
