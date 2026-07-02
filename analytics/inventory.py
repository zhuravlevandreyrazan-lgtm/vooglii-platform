from __future__ import annotations

from typing import Any

from analytics.common import DEFAULT_USER_ID
from analytics.inventory_engine import build_inventory_analysis


def get_inventory_payload(user_id: int = DEFAULT_USER_ID) -> dict[str, Any]:
    return build_inventory_analysis(user_id)
