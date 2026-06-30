"""Read-only helpers for command performance diagnostics."""

from __future__ import annotations

from contextlib import contextmanager
import time

__all__ = [
    "api_call_counter",
    "db_open_counter",
    "build_command_performance_snapshot",
    "perf_timer",
    "performance_text",
]


def _ensure_perf_state(target):
    if not isinstance(target, dict):
        return {}
    target.setdefault("_perf_stack", [])
    target.setdefault("layer_timings", {})
    target.setdefault("db_opens_by_layer", {})
    target.setdefault("db_queries_by_layer", {})
    target.setdefault("api_call_count", {
        "finance_api_calls": 0,
        "ads_api_calls": 0,
        "sales_api_calls": 0,
    })
    target.setdefault("api_calls_by_layer", {})
    return target


@contextmanager
def perf_timer(target, key):
    key = str(key or "")
    state = _ensure_perf_state(target)
    started = time.perf_counter()
    if state:
        stack = list(state.get("_perf_stack") or [])
        stack.append(key)
        state["_perf_stack"] = stack
        state["_active_layer"] = key
    try:
        yield
    finally:
        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 1)
        if state:
            state[key] = round(float(state.get(key) or 0.0) + elapsed_ms, 1)
            layer_timings = state.setdefault("layer_timings", {})
            layer_entry = dict(layer_timings.get(key) or {})
            layer_entry["ms"] = round(float(layer_entry.get("ms") or 0.0) + elapsed_ms, 1)
            layer_entry.setdefault("status", "built")
            layer_entry.setdefault("reused", "no")
            layer_timings[key] = layer_entry
            stack = list(state.get("_perf_stack") or [])
            if stack:
                stack.pop()
            state["_perf_stack"] = stack
            state["_active_layer"] = stack[-1] if stack else None


def _increment_named_bucket(target, bucket_name, key, delta=1):
    state = _ensure_perf_state(target)
    if not state:
        return
    bucket = state.setdefault(bucket_name, {})
    bucket[str(key)] = int(bucket.get(str(key)) or 0) + int(delta or 0)


def _active_layer_name(state):
    state = _ensure_perf_state(state)
    if not state:
        return "unattributed"
    layer_source = state.get("timings") if isinstance(state.get("timings"), dict) else state
    return str(layer_source.get("_active_layer") or state.get("_active_layer") or "unattributed")


@contextmanager
def db_open_counter(sqlite_module, target):
    state = _ensure_perf_state(target)
    original_connect = sqlite_module.connect

    def _counted_connect(*args, **kwargs):
        if state:
            state["db_open_count"] = int(state.get("db_open_count") or 0) + 1
            layer_name = _active_layer_name(state)
            _increment_named_bucket(state, "db_opens_by_layer", layer_name)
        connection = original_connect(*args, **kwargs)

        class _CursorProxy:
            def __init__(self, inner):
                object.__setattr__(self, "_inner", inner)

            def execute(self, *execute_args, **execute_kwargs):
                if state:
                    state["db_query_count"] = int(state.get("db_query_count") or 0) + 1
                    layer_name = _active_layer_name(state)
                    _increment_named_bucket(state, "db_queries_by_layer", layer_name)
                return self._inner.execute(*execute_args, **execute_kwargs)

            def executemany(self, *execute_args, **execute_kwargs):
                if state:
                    state["db_query_count"] = int(state.get("db_query_count") or 0) + 1
                    layer_name = _active_layer_name(state)
                    _increment_named_bucket(state, "db_queries_by_layer", layer_name)
                return self._inner.executemany(*execute_args, **execute_kwargs)

            def __getattr__(self, name):
                return getattr(self._inner, name)

            def __setattr__(self, name, value):
                setattr(self._inner, name, value)

        class _ConnectionProxy:
            def __init__(self, inner):
                object.__setattr__(self, "_inner", inner)

            def cursor(self, *cursor_args, **cursor_kwargs):
                return _CursorProxy(self._inner.cursor(*cursor_args, **cursor_kwargs))

            def __getattr__(self, name):
                return getattr(self._inner, name)

            def __setattr__(self, name, value):
                setattr(self._inner, name, value)

        return _ConnectionProxy(connection)

    sqlite_module.connect = _counted_connect
    try:
        yield
    finally:
        sqlite_module.connect = original_connect


@contextmanager
def api_call_counter(target):
    state = _ensure_perf_state(target)
    yield state


def _warning_list(items):
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


def build_command_performance_snapshot(
    command="director",
    period_label=None,
    mode="full",
    light_path_used=False,
    full_fallback_fields=None,
    saved_db_opens_estimate=0,
    saved_queries_estimate=0,
    timings=None,
    db_open_count=0,
    db_query_count=0,
    db_opens_by_layer=None,
    db_queries_by_layer=None,
    api_call_count=None,
    api_calls_by_layer=None,
    snapshot_build_counts=None,
    layer_timings=None,
    warnings=None,
):
    timings = dict(timings or {})
    snapshot_build_counts = dict(snapshot_build_counts or {})
    layer_timings = dict(layer_timings or {})
    db_opens_by_layer = dict(db_opens_by_layer or {})
    db_queries_by_layer = dict(db_queries_by_layer or {})
    api_call_count = dict(api_call_count or {})
    api_calls_by_layer = dict(api_calls_by_layer or {})
    full_fallback_fields = list(full_fallback_fields or [])
    warnings = _warning_list(warnings)

    total_ms = round(float(timings.get("total_ms") or 0.0), 1)
    if total_ms <= 0.0:
        total_ms = round(sum(float(value or 0.0) for value in timings.values()), 1)

    duplicate_snapshot_builds = [
        {"snapshot": key, "count": int(value or 0)}
        for key, value in sorted(snapshot_build_counts.items())
        if int(value or 0) > 1
    ]

    layer_map = [
        ("access_check_ms", "Access check"),
        ("period_parse_ms", "Period parse"),
        ("finance_status_ms", "Finance status"),
        ("financial_engine_ms", "Financial Engine"),
        ("business_metrics_ms", "Business Metrics"),
        ("udl_ms", "UDL"),
        ("kpi_ms", "KPI"),
        ("cfo_insights_ms", "CFO Insights"),
        ("decision_ms", "Decision Engine"),
        ("advisor_v2_ms", "Advisor v2"),
        ("director_snapshot_ms", "Director snapshot"),
        ("director_render_ms", "Director render"),
    ]
    slowest_layers = [
        {"layer": label, "ms": round(float(timings.get(key) or 0.0), 1)}
        for key, label in layer_map
        if float(timings.get(key) or 0.0) > 0.0
    ]
    slowest_layers.sort(key=lambda item: item["ms"], reverse=True)

    budgets = {
        "director": 1500.0,
        "home": 1500.0,
        "advisor_v2": 1500.0,
        "advisor": 1500.0,
        "decision": 1200.0,
        "cfo_insights": 1200.0,
        "kpi": 1000.0,
        "system_audit": 2000.0,
        "dashboard": 2000.0,
        "report_ceo": 2000.0,
    }
    normalized_command = str(command or "").lower()
    budget_ms = budgets.get(normalized_command)
    if budget_ms and total_ms > budget_ms:
        warnings.append("director above performance budget" if normalized_command == "director" else f"performance budget exceeded: {int(total_ms)} ms > {int(budget_ms)} ms")

    for item in slowest_layers:
        if float(item.get("ms") or 0.0) > 500.0:
            warnings.append(f"slow layer: {item.get('layer')} {float(item.get('ms') or 0.0):.1f} ms")

    if any(int(api_call_count.get(name) or 0) > 0 for name in ("finance_api_calls", "ads_api_calls", "sales_api_calls")):
        warnings.append("external API calls detected during profiling")

    recommendations = []
    if duplicate_snapshot_builds:
        recommendations.append("Есть повторная сборка snapshot внутри одного запроса.")
    if int(db_open_count or 0) > 6:
        recommendations.append("Высокое число открытий SQLite. Стоит расширить reuse готовых snapshot.")
    if slowest_layers:
        top_layer = slowest_layers[0]
        recommendations.append(f"Самый тяжёлый слой: {top_layer['layer']} ({top_layer['ms']:.1f} ms).")
    if budget_ms and total_ms <= budget_ms:
        recommendations.append("Команда укладывается в мягкий performance budget.")
    if not recommendations:
        recommendations.append("Существенных performance-проблем не обнаружено.")

    return {
        "status": "OK",
        "command": str(command or "director"),
        "period": str(period_label or "-"),
        "mode": str(mode or "full"),
        "light_path_used": bool(light_path_used),
        "full_fallback_fields": full_fallback_fields,
        "saved_db_opens_estimate": int(saved_db_opens_estimate or 0),
        "saved_queries_estimate": int(saved_queries_estimate or 0),
        "total_ms": total_ms,
        "access_check_ms": round(float(timings.get("access_check_ms") or 0.0), 1),
        "period_parse_ms": round(float(timings.get("period_parse_ms") or 0.0), 1),
        "finance_status_ms": round(float(timings.get("finance_status_ms") or 0.0), 1),
        "financial_engine_ms": round(float(timings.get("financial_engine_ms") or 0.0), 1),
        "business_metrics_ms": round(float(timings.get("business_metrics_ms") or 0.0), 1),
        "udl_ms": round(float(timings.get("udl_ms") or 0.0), 1),
        "kpi_ms": round(float(timings.get("kpi_ms") or 0.0), 1),
        "cfo_insights_ms": round(float(timings.get("cfo_insights_ms") or 0.0), 1),
        "decision_ms": round(float(timings.get("decision_ms") or 0.0), 1),
        "advisor_v2_ms": round(float(timings.get("advisor_v2_ms") or 0.0), 1),
        "director_snapshot_ms": round(float(timings.get("director_snapshot_ms") or 0.0), 1),
        "director_render_ms": round(float(timings.get("director_render_ms") or 0.0), 1),
        "db_open_count": int(db_open_count or 0),
        "db_query_count": int(db_query_count or 0),
        "db_opens_by_layer": db_opens_by_layer,
        "db_queries_by_layer": db_queries_by_layer,
        "api_call_count": {
            "finance_api_calls": int(api_call_count.get("finance_api_calls") or 0),
            "ads_api_calls": int(api_call_count.get("ads_api_calls") or 0),
            "sales_api_calls": int(api_call_count.get("sales_api_calls") or 0),
        },
        "api_calls_by_layer": api_calls_by_layer,
        "snapshot_build_counts": snapshot_build_counts,
        "duplicate_snapshot_builds": duplicate_snapshot_builds,
        "layer_timings": layer_timings,
        "slowest_layers": slowest_layers[:5],
        "recommendations": recommendations,
        "warnings": _warning_list(warnings),
        "budget_ms": budget_ms,
    }


def performance_text(snapshot):
    snapshot = dict(snapshot or {})
    slowest_layers = list(snapshot.get("slowest_layers") or [])
    duplicate_snapshot_builds = list(snapshot.get("duplicate_snapshot_builds") or [])
    recommendations = list(snapshot.get("recommendations") or [])
    warnings = list(snapshot.get("warnings") or [])
    counts = dict(snapshot.get("snapshot_build_counts") or {})
    layer_timings = dict(snapshot.get("layer_timings") or {})
    api_call_count = dict(snapshot.get("api_call_count") or {})
    db_opens_by_layer = dict(snapshot.get("db_opens_by_layer") or {})
    db_queries_by_layer = dict(snapshot.get("db_queries_by_layer") or {})

    lines = [
        "PERFORMANCE SNAPSHOT",
        "",
        f"Command: {snapshot.get('command') or 'director'}",
        f"Period: {snapshot.get('period') or '-'}",
        f"Mode: {snapshot.get('mode') or 'full'}",
        f"Light path used: {'yes' if snapshot.get('light_path_used') else 'no'}",
        f"Full fallback fields: {snapshot.get('full_fallback_fields') or []}",
        f"Saved DB opens estimate: {int(snapshot.get('saved_db_opens_estimate') or 0)}",
        f"Saved queries estimate: {int(snapshot.get('saved_queries_estimate') or 0)}",
        f"Total: {float(snapshot.get('total_ms') or 0.0):.1f} ms",
        f"DB opens: {int(snapshot.get('db_open_count') or 0)}",
        f"DB queries: {int(snapshot.get('db_query_count') or 0)}",
        "",
        "Slowest layers:",
    ]
    if slowest_layers:
        for item in slowest_layers:
            lines.append(f"- {item.get('layer')}: {float(item.get('ms') or 0.0):.1f} ms")
    else:
        lines.append("- no data")

    lines.extend(["", "Layer timings:"])
    if layer_timings:
        for key in sorted(layer_timings):
            item = dict(layer_timings.get(key) or {})
            lines.append(
                f"- {key}: {float(item.get('ms') or 0.0):.1f} ms | status={item.get('status') or 'unknown'} | reused={item.get('reused') or 'no'}"
            )
    else:
        lines.append("- no data")

    lines.extend(["", "Snapshot reuse:"])
    if counts:
        for name, value in sorted(counts.items()):
            lines.append(f"- {name}: {int(value or 0)}")
    else:
        lines.append("- no data")

    lines.extend(["", "duplicate snapshot builds:"])
    if duplicate_snapshot_builds:
        for item in duplicate_snapshot_builds:
            lines.append(f"- {item.get('snapshot')}: {int(item.get('count') or 0)}")
    else:
        lines.append("- none")

    lines.extend(["", "DB by layer:"])
    if db_opens_by_layer:
        for key in sorted(db_opens_by_layer):
            lines.append(
                f"- {key}: opens={int(db_opens_by_layer.get(key) or 0)}, queries={int(db_queries_by_layer.get(key) or 0)}"
            )
    else:
        lines.append("- no data")

    lines.extend(["", "API calls:"])
    lines.append(f"- finance_api_calls: {int(api_call_count.get('finance_api_calls') or 0)}")
    lines.append(f"- ads_api_calls: {int(api_call_count.get('ads_api_calls') or 0)}")
    lines.append(f"- sales_api_calls: {int(api_call_count.get('sales_api_calls') or 0)}")

    lines.extend(["", "Recommendations:"])
    for item in recommendations or ["No recommendations."]:
        lines.append(f"- {item}")

    lines.extend(["", "Warnings:"])
    if warnings:
        for item in warnings:
            lines.append(f"- {item}")
    else:
        lines.append("- no warnings")

    return "\n".join(lines)
