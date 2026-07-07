from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from product_catalog import build_product_catalog_audit


def _money(value) -> str:
    try:
        return f"{float(value or 0):,.2f}".replace(",", " ")
    except Exception:
        return str(value)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", required=True, type=int)
    parser.add_argument("--from", dest="date_from")
    parser.add_argument("--to", dest="date_to")
    args = parser.parse_args()
    period = (args.date_from, args.date_to) if args.date_from and args.date_to else None
    audit = build_product_catalog_audit(args.user_id, period=period)
    print("Product Catalog v2")
    print()
    print(f"Период: {audit.get('period')}")
    print(f"Всего товаров: {int(audit.get('catalog_rows') or 0)}")
    print(f"С себестоимостью: {int(audit.get('rows_with_cost') or 0)}")
    print(f"Без себестоимости: {int(audit.get('rows_without_cost') or 0)}")
    print(f"Связь с продажами: {float(audit.get('coverage_percent') or 0):.1f}%")
    print()
    print("Top missing cost:")
    rows = list(audit.get("top_missing_cost") or [])
    if not rows:
        print("none")
    else:
        for row in rows:
            print(
                f"nm_id={row.get('nm_id') or '-'} | "
                f"supplier_article={row.get('supplier_article') or '-'} | "
                f"barcode={row.get('barcode') or '-'} | "
                f"quantity={int(row.get('quantity') or 0)} | "
                f"revenue={_money(row.get('revenue'))} | "
                f"reason=cost_price missing or product not in catalog"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
