from .unified_snapshot import (
    FINANCE_STATUS_LABELS,
    FINANCE_STATUS_TEXT,
    UnifiedFinancialSnapshot,
    build_consistency_audit,
    build_unified_financial_snapshot,
    build_unified_financial_snapshot_dict,
)


def build_customer_financial_snapshot(*args, **kwargs):
    from .customer_snapshot import build_customer_financial_snapshot as _impl

    return _impl(*args, **kwargs)


def build_customer_snapshot(*args, **kwargs):
    from .customer_snapshot import build_customer_snapshot as _impl

    return _impl(*args, **kwargs)


def build_customer_financial_snapshot_dict(*args, **kwargs):
    from .customer_snapshot import build_customer_financial_snapshot_dict as _impl

    return _impl(*args, **kwargs)

__all__ = [
    "build_customer_financial_snapshot",
    "build_customer_snapshot",
    "build_customer_financial_snapshot_dict",
    "FINANCE_STATUS_LABELS",
    "FINANCE_STATUS_TEXT",
    "UnifiedFinancialSnapshot",
    "build_consistency_audit",
    "build_unified_financial_snapshot",
    "build_unified_financial_snapshot_dict",
]
