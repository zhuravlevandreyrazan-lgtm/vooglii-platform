"""Read-only project structure and performance snapshots for release prep."""

from __future__ import annotations

import ast
from collections import Counter, defaultdict
from pathlib import Path

__all__ = [
    "build_project_structure_snapshot",
    "build_project_structure_readiness_snapshot",
    "build_performance_snapshot",
    "project_structure_readiness_text",
]


def _py_files(project_root):
    root = Path(project_root)
    excluded_parts = {
        ".git",
        "__pycache__",
        ".tmp_uncompyle6_master",
        ".venv",
        "venv",
        "env",
        ".mypy_cache",
        ".pytest_cache",
        "site-packages",
    }
    return [
        path for path in root.rglob("*.py")
        if not any(part in excluded_parts or part.startswith(".tmp") for part in path.parts)
    ]


def _read_text(path):
    try:
        return path.read_text(encoding="utf-8-sig")
    except Exception:
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return path.read_text(errors="ignore")


def _line_count(path):
    return len(_read_text(path).splitlines())


def _module_label(project_root, path):
    try:
        return str(path.relative_to(project_root)).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def _ast_tree(path):
    try:
        return ast.parse(_read_text(path), filename=str(path))
    except SyntaxError:
        return None


def _function_spans(path):
    tree = _ast_tree(path)
    if tree is None:
        return []
    spans = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end_lineno = getattr(node, "end_lineno", node.lineno)
            spans.append({
                "name": node.name,
                "start": int(node.lineno),
                "end": int(end_lineno),
                "lines": int(end_lineno - node.lineno + 1),
            })
    return spans


def _import_diagnostics(path):
    tree = _ast_tree(path)
    if tree is None:
        return {"unused": [], "duplicates": []}
    imported = {}
    used = set()
    duplicates = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name.split(".")[0]
                if name in imported:
                    duplicates.append(name)
                imported[name] = alias.name
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                name = alias.asname or alias.name
                if name in imported:
                    duplicates.append(name)
                imported[name] = f"{node.module or ''}.{alias.name}"
    unused = sorted(name for name in imported if name not in used)
    return {"unused": unused, "duplicates": sorted(set(duplicates))}


def build_project_structure_snapshot(project_root):
    project_root = Path(project_root)
    files = _py_files(project_root)
    line_counts = {path: _line_count(path) for path in files}

    function_locations = defaultdict(list)
    large_functions = []
    legacy_helpers = []
    repeated_blocks = []
    duplicate_imports = []
    unused_imports = []

    for path in files:
        label = _module_label(project_root, path)
        for span in _function_spans(path):
            function_locations[span["name"]].append(label)
            if span["lines"] > 200:
                large_functions.append({
                    "module": label,
                    "function": span["name"],
                    "lines": span["lines"],
                })
            if span["name"].startswith("_legacy"):
                legacy_helpers.append(f"{label}:{span['name']}")
        text = _read_text(path)
        for marker in ("_period_help(", "await access(", "send_long(update", "reply_text("):
            count = text.count(marker)
            if count >= 5:
                repeated_blocks.append(f"{label}: repeated '{marker}' x{count}")
        import_diag = _import_diagnostics(path)
        if import_diag["duplicates"]:
            duplicate_imports.append({"module": label, "imports": import_diag["duplicates"]})
        if import_diag["unused"]:
            unused_imports.append({"module": label, "imports": import_diag["unused"][:20]})

    duplicate_helpers = [
        {"name": name, "modules": modules}
        for name, modules in sorted(function_locations.items())
        if len(modules) > 1
    ]

    large_files = [
        {"module": _module_label(project_root, path), "lines": line_counts[path]}
        for path in sorted(files, key=lambda item: line_counts[item], reverse=True)
        if line_counts[path] > 1500
    ]

    core_modules = [
        "wb_agent/financial_engine.py",
        "wb_agent/business_metrics.py",
        "wb_agent/unified_data_layer.py",
        "wb_agent/period_engine.py",
        "wb_agent/sku_registry.py",
        "wb_agent/kpi_engine.py",
        "wb_agent/cfo_insights.py",
        "wb_agent/decision_engine.py",
        "wb_agent/advisor_v2.py",
        "wb_agent/director.py",
    ]
    existing_core = [item for item in core_modules if (project_root / item).exists()]

    legacy_modules = sorted(
        _module_label(project_root, path)
        for path in files
        if "legacy" in path.stem.lower() or path.name == "report.py"
    )

    return {
        "status": "OK",
        "core_modules": existing_core,
        "legacy_modules": legacy_modules,
        "deprecated_helpers": sorted(legacy_helpers),
        "duplicate_helpers": duplicate_helpers,
        "unused_imports": unused_imports[:20],
        "duplicate_imports": duplicate_imports[:20],
        "large_files": large_files,
        "large_functions": sorted(large_functions, key=lambda item: item["lines"], reverse=True)[:30],
        "repeated_code_blocks": repeated_blocks[:40],
    }


def build_project_structure_readiness_snapshot(project_root, performance_snapshot=None):
    project_root = Path(project_root)
    structure_snapshot = build_project_structure_snapshot(project_root)
    performance_snapshot = dict(performance_snapshot or {})

    large_files = list(structure_snapshot.get("large_files") or [])
    duplicate_helpers = list(structure_snapshot.get("duplicate_helpers") or [])
    repeated_code_blocks = list(structure_snapshot.get("repeated_code_blocks") or [])
    duplicate_snapshot_builds = list(((performance_snapshot.get("snapshot_reuse") or {}).get("duplicate_snapshot_builds") or []))
    telegram_startup = dict(performance_snapshot.get("telegram_startup") or {})
    telegram_line_count = int(telegram_startup.get("line_count") or 0)

    blockers = []
    warnings = []
    if duplicate_snapshot_builds:
        blockers.append("Director snapshot reuse still reports duplicate builds.")
    if telegram_line_count > 12000:
        warnings.append("telegram_bot.py is still a very large router and remains the main refactor hotspot.")
    if large_files:
        warnings.append("Several Python modules are still large and reduce release-time maintainability.")
    if duplicate_helpers:
        warnings.append("Duplicate helper names exist across modules and increase structure ambiguity.")
    if repeated_code_blocks:
        warnings.append("Repeated router/help/send patterns still indicate partial modularization.")

    if blockers:
        status = "BLOCKED"
    elif warnings:
        status = "WARNING"
    else:
        status = "READY"

    return {
        "status": status,
        "core_modules_ready": len(list(structure_snapshot.get("core_modules") or [])) >= 8,
        "router_status": "WARNING" if telegram_line_count > 12000 else "READY",
        "modularization_status": "WARNING" if duplicate_helpers or repeated_code_blocks else "READY",
        "performance_status": str(performance_snapshot.get("status") or "UNKNOWN"),
        "large_file_count": len(large_files),
        "large_function_count": len(list(structure_snapshot.get("large_functions") or [])),
        "duplicate_helper_count": len(duplicate_helpers),
        "duplicate_snapshot_builds": duplicate_snapshot_builds,
        "blockers": blockers,
        "warnings": warnings,
        "recommended_next_step": (
            "Keep Control Center as the release entrypoint and continue moving router diagnostics into wb_agent modules."
            if status != "READY"
            else "Project structure is ready for release-candidate read-only operation."
        ),
        "structure_snapshot": structure_snapshot,
        "performance_snapshot": performance_snapshot,
    }


def build_performance_snapshot(project_root, director_build_counts=None):
    project_root = Path(project_root)
    files = _py_files(project_root)
    line_counts = {path: _line_count(path) for path in files}

    largest_modules = [
        {"module": _module_label(project_root, path), "lines": line_counts[path]}
        for path in sorted(files, key=lambda item: line_counts[item], reverse=True)[:10]
    ]

    import_counts = Counter()
    telegram_bot_path = project_root / "telegram_bot.py"
    if telegram_bot_path.exists():
        tree = _ast_tree(telegram_bot_path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    import_counts[alias.name.split(".")[0]] += 1
            elif isinstance(node, ast.ImportFrom):
                import_counts[node.module or ""] += len(node.names)

    director_build_counts = dict(director_build_counts or {})
    duplicate_snapshot_builds = [
        {"snapshot": key, "count": value}
        for key, value in sorted(director_build_counts.items())
        if int(value or 0) > 1
    ]

    slowest_commands = [
        {"command": "/director", "reason": "builds executive stack"},
        {"command": "/advisor v2", "reason": "builds advisory stack"},
        {"command": "/decision", "reason": "builds scenario stack"},
        {"command": "/cfo insights", "reason": "builds insight stack"},
        {"command": "/kpi", "reason": "builds KPI stack"},
    ]

    return {
        "status": "OK",
        "telegram_startup": {
            "main_module": "telegram_bot.py",
            "line_count": line_counts.get(telegram_bot_path, 0),
            "import_count": int(sum(import_counts.values())),
        },
        "largest_modules": largest_modules,
        "slowest_commands": slowest_commands,
        "snapshot_reuse": {
            "director_build_counts": director_build_counts,
            "duplicate_snapshot_builds": duplicate_snapshot_builds,
        },
        "estimated_optimization": [
            "Director now reuses prebuilt snapshots inside one request.",
            "Executive commands share preset-aware period parsing.",
            "Large router file still remains the main technical debt hotspot.",
        ],
        "memory_hotspots": [item["module"] for item in largest_modules[:5]],
        "import_hotspots": [
            {"module": module, "count": count}
            for module, count in import_counts.most_common(10)
        ],
    }


def project_structure_readiness_text(snapshot):
    snapshot = dict(snapshot or {})
    lines = [
        "PROJECT STRUCTURE READINESS",
        "",
        f'status: {snapshot.get("status") or "WARNING"}',
        f'core modules ready: {"yes" if snapshot.get("core_modules_ready") else "no"}',
        f'router status: {snapshot.get("router_status") or "UNKNOWN"}',
        f'modularization status: {snapshot.get("modularization_status") or "UNKNOWN"}',
        f'performance status: {snapshot.get("performance_status") or "UNKNOWN"}',
        f'large files: {int(snapshot.get("large_file_count") or 0)}',
        f'large functions: {int(snapshot.get("large_function_count") or 0)}',
        f'duplicate helpers: {int(snapshot.get("duplicate_helper_count") or 0)}',
        "",
        "Blockers:",
    ]
    blockers = list(snapshot.get("blockers") or [])
    if blockers:
        lines.extend(f"- {item}" for item in blockers)
    else:
        lines.append("- none")
    lines.extend(["", "Warnings:"])
    warnings = list(snapshot.get("warnings") or [])
    if warnings:
        lines.extend(f"- {item}" for item in warnings)
    else:
        lines.append("- none")
    lines.extend([
        "",
        "Recommended next step:",
        str(snapshot.get("recommended_next_step") or "-"),
    ])
    return "\n".join(lines)
