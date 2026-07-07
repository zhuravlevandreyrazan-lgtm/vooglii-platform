from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from hashlib import sha1
from typing import Any

from config import DB_NAME
from db_manager import init_db


CATALOG_SYNC_OK = "OK"
CATALOG_SYNC_PARTIAL = "PARTIAL"
CATALOG_SYNC_MISSING_COST_VALUES = "MISSING_COST_VALUES"


def _conn() -> sqlite3.Connection:
    init_db()
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _float(value: Any) -> float:
    try:
        return round(float(value or 0), 2)
    except Exception:
        return 0.0


def _int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except Exception:
        return None


def _synthetic_nm_id(user_id: int, supplier_article: str | None, barcode: str | None) -> int:
    base = f"{int(user_id)}|{supplier_article or ''}|{barcode or ''}"
    digest = sha1(base.encode("utf-8")).hexdigest()[:15]
    return -max(1, int(digest, 16))


def _infer_nm_ids(cur: sqlite3.Cursor, user_id: int, supplier_article: str | None) -> list[int]:
    article = _text(supplier_article)
    if not article:
        return []
    rows = cur.execute(
        """
        SELECT DISTINCT nm_id
        FROM (
            SELECT nm_id FROM sales WHERE telegram_id=? AND supplier_article=?
            UNION ALL
            SELECT nm_id FROM orders WHERE telegram_id=? AND supplier_article=?
            UNION ALL
            SELECT nm_id FROM stocks WHERE telegram_id=? AND supplier_article=?
            UNION ALL
            SELECT nm_id FROM advertising WHERE telegram_id=? AND supplier_article=?
        )
        WHERE nm_id IS NOT NULL AND CAST(nm_id AS TEXT)!=''
        ORDER BY nm_id
        """,
        (int(user_id), article, int(user_id), article, int(user_id), article, int(user_id), article),
    ).fetchall()
    result: list[int] = []
    for row in rows:
        nm_id = _int(row[0])
        if nm_id is not None and nm_id not in result:
            result.append(nm_id)
    return result


def _upsert_catalog_row(
    cur: sqlite3.Cursor,
    user_id: int,
    nm_id: int,
    *,
    supplier_article: str | None = None,
    barcode: str | None = None,
    brand: str | None = None,
    subject: str | None = None,
    tech_size: str | None = None,
    name: str | None = None,
    cost_price: float | None = None,
    last_price: float | None = None,
    source: str | None = None,
    preserve_cost: bool = True,
) -> str:
    existing = cur.execute(
        "SELECT * FROM product_catalog WHERE user_id=? AND nm_id=?",
        (int(user_id), int(nm_id)),
    ).fetchone()
    now = _now()
    incoming_cost = None if cost_price is None else _float(cost_price)
    incoming_last_price = None if last_price is None else _float(last_price)
    if existing:
        current_cost = _float(existing["cost_price"])
        next_cost = current_cost if preserve_cost and current_cost > 0 and (incoming_cost or 0) <= 0 else current_cost
        if incoming_cost is not None and (not preserve_cost or current_cost <= 0):
            next_cost = incoming_cost
        next_last_price = incoming_last_price if incoming_last_price not in (None, 0.0) else _float(existing["last_price"])
        cur.execute(
            """
            UPDATE product_catalog
            SET
                supplier_article=COALESCE(?, supplier_article),
                barcode=COALESCE(?, barcode),
                brand=COALESCE(?, brand),
                subject=COALESCE(?, subject),
                tech_size=COALESCE(?, tech_size),
                name=COALESCE(?, name),
                cost_price=?,
                last_price=?,
                source=COALESCE(?, source),
                updated_at=?
            WHERE user_id=? AND nm_id=?
            """,
            (
                _text(supplier_article),
                _text(barcode),
                _text(brand),
                _text(subject),
                _text(tech_size),
                _text(name),
                next_cost,
                next_last_price,
                _text(source),
                now,
                int(user_id),
                int(nm_id),
            ),
        )
        return "updated"
    cur.execute(
        """
        INSERT INTO product_catalog(
            user_id, nm_id, supplier_article, barcode, brand, subject, tech_size, name,
            cost_price, last_price, source, created_at, updated_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            int(user_id),
            int(nm_id),
            _text(supplier_article),
            _text(barcode),
            _text(brand),
            _text(subject),
            _text(tech_size),
            _text(name),
            _float(incoming_cost),
            _float(incoming_last_price),
            _text(source),
            now,
            now,
        ),
    )
    return "inserted"


def _transfer_legacy_cost(cur: sqlite3.Cursor, user_id: int, nm_id: int, supplier_article: str | None, barcode: str | None) -> bool:
    article = _text(supplier_article)
    code = _text(barcode)
    if not article and not code:
        return False
    legacy_rows = cur.execute(
        """
        SELECT nm_id, cost_price, last_price
        FROM product_catalog
        WHERE user_id=?
          AND nm_id < 0
          AND (
              (? IS NOT NULL AND supplier_article=?)
              OR (? IS NOT NULL AND barcode=?)
          )
        ORDER BY updated_at DESC, created_at DESC
        """,
        (int(user_id), article, article, code, code),
    ).fetchall()
    if not legacy_rows:
        return False
    existing = cur.execute(
        "SELECT cost_price, last_price FROM product_catalog WHERE user_id=? AND nm_id=?",
        (int(user_id), int(nm_id)),
    ).fetchone()
    if not existing:
        return False
    current_cost = _float(existing["cost_price"])
    current_last_price = _float(existing["last_price"])
    adopted = False
    for row in legacy_rows:
        legacy_cost = _float(row["cost_price"])
        legacy_last_price = _float(row["last_price"])
        if current_cost <= 0 and legacy_cost > 0:
            cur.execute(
                "UPDATE product_catalog SET cost_price=?, updated_at=? WHERE user_id=? AND nm_id=?",
                (legacy_cost, _now(), int(user_id), int(nm_id)),
            )
            current_cost = legacy_cost
            adopted = True
        if current_last_price <= 0 and legacy_last_price > 0:
            cur.execute(
                "UPDATE product_catalog SET last_price=?, updated_at=? WHERE user_id=? AND nm_id=?",
                (legacy_last_price, _now(), int(user_id), int(nm_id)),
            )
            current_last_price = legacy_last_price
        cur.execute(
            "DELETE FROM product_catalog WHERE user_id=? AND nm_id=?",
            (int(user_id), int(row["nm_id"])),
        )
    return adopted


def migrate_legacy_products(user_id: int) -> dict[str, Any]:
    conn = _conn()
    try:
        cur = conn.cursor()
        rows = cur.execute(
            """
            SELECT telegram_id, supplier_article, cost_price, last_price
            FROM products
            WHERE telegram_id IN (?, 0)
            ORDER BY CASE WHEN telegram_id=? THEN 0 ELSE 1 END, supplier_article
            """,
            (int(user_id), int(user_id)),
        ).fetchall()
        inserted = 0
        updated = 0
        warnings: list[dict[str, Any]] = []
        for row in rows:
            row_user_id = int(row["telegram_id"] or 0)
            article = _text(row["supplier_article"])
            nm_ids = _infer_nm_ids(cur, row_user_id if row_user_id != 0 else int(user_id), article)
            if len(nm_ids) == 1:
                result = _upsert_catalog_row(
                    cur,
                    row_user_id,
                    nm_ids[0],
                    supplier_article=article,
                    cost_price=row["cost_price"],
                    last_price=row["last_price"],
                    source="legacy_products_resolved",
                    preserve_cost=True,
                )
            else:
                synthetic_nm_id = _synthetic_nm_id(row_user_id, article, None)
                result = _upsert_catalog_row(
                    cur,
                    row_user_id,
                    synthetic_nm_id,
                    supplier_article=article,
                    cost_price=row["cost_price"],
                    last_price=row["last_price"],
                    source="legacy_products_unresolved",
                    preserve_cost=True,
                )
                if len(nm_ids) > 1:
                    warnings.append(
                        {
                            "user_id": row_user_id,
                            "supplier_article": article,
                            "reason": "multiple_nm_id_candidates",
                            "nm_ids": nm_ids,
                        }
                    )
            if result == "inserted":
                inserted += 1
            else:
                updated += 1
        conn.commit()
        return {
            "status": "OK",
            "inserted": inserted,
            "updated": updated,
            "warnings": warnings,
        }
    finally:
        conn.close()


def enrich_product_catalog(user_id: int) -> dict[str, Any]:
    conn = _conn()
    try:
        cur = conn.cursor()
        rows = cur.execute(
            """
            SELECT nm_id, supplier_article, barcode, brand, category AS subject, NULL AS tech_size,
                   supplier_article AS name, MAX(COALESCE(price_with_disc, 0)) AS last_price, 'sales' AS source
            FROM sales
            WHERE telegram_id=? AND nm_id IS NOT NULL
            GROUP BY nm_id, supplier_article, barcode, brand, category
            UNION ALL
            SELECT nm_id, supplier_article, barcode, brand, category AS subject, NULL AS tech_size,
                   supplier_article AS name, MAX(COALESCE(price_with_disc, 0)) AS last_price, 'orders' AS source
            FROM orders
            WHERE telegram_id=? AND nm_id IS NOT NULL
            GROUP BY nm_id, supplier_article, barcode, brand, category
            UNION ALL
            SELECT nm_id, supplier_article, barcode, NULL AS brand, NULL AS subject, NULL AS tech_size,
                   supplier_article AS name, 0 AS last_price, 'stocks' AS source
            FROM stocks
            WHERE telegram_id=? AND nm_id IS NOT NULL
            GROUP BY nm_id, supplier_article, barcode
            UNION ALL
            SELECT nm_id, supplier_article, NULL AS barcode, NULL AS brand, NULL AS subject, app_type AS tech_size,
                   name, MAX(COALESCE(sum_price, 0)) AS last_price, 'advertising' AS source
            FROM advertising
            WHERE telegram_id=? AND nm_id IS NOT NULL
            GROUP BY nm_id, supplier_article, app_type, name
            """,
            (int(user_id), int(user_id), int(user_id), int(user_id)),
        ).fetchall()
        inserted = 0
        updated = 0
        transferred_cost = 0
        for row in rows:
            nm_id = _int(row["nm_id"])
            if nm_id is None or nm_id <= 0:
                continue
            result = _upsert_catalog_row(
                cur,
                int(user_id),
                nm_id,
                supplier_article=row["supplier_article"],
                barcode=row["barcode"],
                brand=row["brand"],
                subject=row["subject"],
                tech_size=row["tech_size"],
                name=row["name"],
                last_price=row["last_price"],
                source=row["source"],
                preserve_cost=True,
            )
            if _transfer_legacy_cost(cur, int(user_id), nm_id, row["supplier_article"], row["barcode"]):
                transferred_cost += 1
            if result == "inserted":
                inserted += 1
            else:
                updated += 1
        conn.commit()
        return {
            "status": "OK",
            "inserted": inserted,
            "updated": updated,
            "transferred_cost": transferred_cost,
        }
    finally:
        conn.close()


def match_product(user_id: int, nm_id: Any = None, supplier_article: Any = None, barcode: Any = None) -> dict[str, Any] | None:
    conn = _conn()
    try:
        cur = conn.cursor()
        nm_value = _int(nm_id)
        article = _text(supplier_article)
        code = _text(barcode)
        rows = cur.execute(
            """
            SELECT *,
                   CASE
                       WHEN ? IS NOT NULL AND nm_id=? THEN 1
                       WHEN ? IS NOT NULL AND supplier_article=? THEN 2
                       WHEN ? IS NOT NULL AND barcode=? THEN 3
                       ELSE 9
                   END AS priority
            FROM product_catalog
            WHERE user_id=?
              AND (
                  (? IS NOT NULL AND nm_id=?)
                  OR (? IS NOT NULL AND supplier_article=?)
                  OR (? IS NOT NULL AND barcode=?)
              )
            ORDER BY priority ASC, updated_at DESC, created_at DESC
            LIMIT 1
            """,
            (
                nm_value,
                nm_value,
                article,
                article,
                code,
                code,
                int(user_id),
                nm_value,
                nm_value,
                article,
                article,
                code,
                code,
            ),
        ).fetchall()
        if rows:
            return dict(rows[0])
        row = cur.execute(
            """
            SELECT cost_price
            FROM products
            WHERE telegram_id IN (?,0) AND supplier_article=?
            ORDER BY telegram_id DESC
            LIMIT 1
            """,
            (int(user_id), article),
        ).fetchone() if article else None
        if row:
            return {
                "user_id": int(user_id),
                "nm_id": None,
                "supplier_article": article,
                "barcode": code,
                "cost_price": _float(row["cost_price"] if isinstance(row, sqlite3.Row) else row[0]),
                "source": "legacy_products_fallback",
            }
        return None
    finally:
        conn.close()


def get_cost_price(user_id: int, nm_id: Any = None, supplier_article: Any = None, barcode: Any = None) -> float | None:
    row = match_product(user_id, nm_id=nm_id, supplier_article=supplier_article, barcode=barcode)
    if not row:
        return None
    value = _float(row.get("cost_price"))
    return value if value > 0 else None


def list_catalog_products(user_id: int, with_cost_only: bool = False) -> list[dict[str, Any]]:
    conn = _conn()
    try:
        cur = conn.cursor()
        query = """
            SELECT
                user_id,
                nm_id,
                supplier_article,
                barcode,
                brand,
                subject,
                cost_price,
                last_price,
                source,
                updated_at
            FROM product_catalog
            WHERE user_id=?
        """
        params: list[Any] = [int(user_id)]
        if with_cost_only:
            query += " AND COALESCE(cost_price,0)>0"
        query += " ORDER BY COALESCE(supplier_article,''), nm_id"
        rows = cur.execute(query, tuple(params)).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def set_cost_price(identifier: str | int, cost_price: float, user_id: int = 0) -> dict[str, Any]:
    conn = _conn()
    try:
        cur = conn.cursor()
        raw_identifier = str(identifier or "").strip()
        nm_id = _int(raw_identifier)
        article = None if nm_id is not None else _text(raw_identifier)
        matched = match_product(int(user_id), nm_id=nm_id, supplier_article=article, barcode=article)
        if matched:
            target_nm_id = _int(matched.get("nm_id"))
            if target_nm_id is None:
                target_nm_id = _synthetic_nm_id(int(user_id), article, None)
            _upsert_catalog_row(
                cur,
                int(user_id),
                int(target_nm_id),
                supplier_article=matched.get("supplier_article") or article,
                barcode=matched.get("barcode"),
                brand=matched.get("brand"),
                subject=matched.get("subject"),
                tech_size=matched.get("tech_size"),
                name=matched.get("name"),
                cost_price=cost_price,
                last_price=matched.get("last_price"),
                source="manual_cost_set",
                preserve_cost=False,
            )
            supplier_article = _text(matched.get("supplier_article") or article)
        else:
            target_nm_id = nm_id if nm_id is not None else _synthetic_nm_id(int(user_id), article, None)
            supplier_article = article
            _upsert_catalog_row(
                cur,
                int(user_id),
                int(target_nm_id),
                supplier_article=supplier_article,
                cost_price=cost_price,
                source="manual_cost_set",
                preserve_cost=False,
            )
        cur.execute(
            """
            INSERT INTO price_history(telegram_id, event_date, supplier_article, price, cost_price, source)
            VALUES(?,?,?,?,?,?)
            """,
            (
                int(user_id),
                _now(),
                supplier_article,
                0,
                _float(cost_price),
                "product_catalog_v2.set_cost",
            ),
        )
        conn.commit()
        return {
            "status": "OK",
            "user_id": int(user_id),
            "nm_id": target_nm_id,
            "supplier_article": supplier_article,
            "cost_price": _float(cost_price),
        }
    finally:
        conn.close()


def get_cost_map(user_id: int) -> dict[str, float]:
    conn = _conn()
    try:
        cur = conn.cursor()
        rows = cur.execute(
            """
            SELECT supplier_article, MAX(COALESCE(cost_price,0)) AS cost_price
            FROM product_catalog
            WHERE user_id IN (?,0) AND supplier_article IS NOT NULL AND TRIM(supplier_article)!=''
            GROUP BY supplier_article
            ORDER BY supplier_article
            """,
            (int(user_id),),
        ).fetchall()
        result: dict[str, float] = {}
        for row in rows:
            article = _text(row["supplier_article"])
            if article and article not in result:
                result[article] = _float(row["cost_price"])
        if result:
            return result
        rows = cur.execute(
            """
            SELECT supplier_article, MAX(COALESCE(cost_price,0)) AS cost_price
            FROM products
            WHERE telegram_id IN (?,0) AND supplier_article IS NOT NULL AND TRIM(supplier_article)!=''
            GROUP BY supplier_article
            ORDER BY supplier_article
            """,
            (int(user_id),),
        ).fetchall()
        return {_text(row["supplier_article"]): _float(row["cost_price"]) for row in rows if _text(row["supplier_article"])}
    finally:
        conn.close()


def sync_product_catalog(user_id: int, period: int | tuple[str, str] | None = None) -> dict[str, Any]:
    migrate_stats = migrate_legacy_products(int(user_id))
    enrich_stats = enrich_product_catalog(int(user_id))
    audit = build_product_catalog_audit(int(user_id), period=period)
    coverage = float(audit.get("coverage_percent") or 0)
    missing = int(audit.get("missing_cost_skus") or 0)
    if missing <= 0 and coverage >= 95:
        status = CATALOG_SYNC_OK
    elif coverage > 0:
        status = CATALOG_SYNC_PARTIAL
    else:
        status = CATALOG_SYNC_MISSING_COST_VALUES
    return {
        "status": status,
        "inserted": int(migrate_stats.get("inserted") or 0) + int(enrich_stats.get("inserted") or 0),
        "updated": int(migrate_stats.get("updated") or 0) + int(enrich_stats.get("updated") or 0),
        "skipped": 0,
        "invalid": len(list(migrate_stats.get("warnings") or [])),
        "source_rows": int(audit.get("catalog_rows") or 0),
        "meta": {
            "migration": migrate_stats,
            "enrich": enrich_stats,
            "coverage_percent": coverage,
            "missing_cost_skus": missing,
            "period": audit.get("period"),
        },
    }


def build_product_catalog_audit(user_id: int, period: int | tuple[str, str] | None = None, limit: int = 20) -> dict[str, Any]:
    conn = _conn()
    try:
        cur = conn.cursor()
        if isinstance(period, tuple) and len(period) == 2:
            date_from, date_to = str(period[0]), str(period[1])
        else:
            days = max(1, int(period or 30))
            date_to = datetime.now().strftime("%Y-%m-%d")
            date_from = (datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
            date_from = (date_from - timedelta(days=days - 1)).strftime("%Y-%m-%d")
        cost_expr = (
            "COALESCE(("
            "SELECT pc.cost_price FROM product_catalog pc "
            "WHERE pc.user_id=s.telegram_id AND s.nm_id IS NOT NULL AND pc.nm_id=s.nm_id "
            "ORDER BY pc.updated_at DESC LIMIT 1"
            "),("
            "SELECT pc.cost_price FROM product_catalog pc "
            "WHERE pc.user_id=s.telegram_id AND TRIM(COALESCE(s.supplier_article,''))!='' AND pc.supplier_article=s.supplier_article "
            "ORDER BY pc.updated_at DESC LIMIT 1"
            "),("
            "SELECT pc.cost_price FROM product_catalog pc "
            "WHERE pc.user_id=s.telegram_id AND TRIM(COALESCE(s.barcode,''))!='' AND pc.barcode=s.barcode "
            "ORDER BY pc.updated_at DESC LIMIT 1"
            "),0)"
        )
        catalog = cur.execute(
            """
            SELECT
                COUNT(*) AS catalog_rows,
                SUM(CASE WHEN COALESCE(cost_price,0)>0 THEN 1 ELSE 0 END) AS rows_with_cost,
                SUM(CASE WHEN COALESCE(cost_price,0)<=0 THEN 1 ELSE 0 END) AS rows_without_cost
            FROM product_catalog
            WHERE user_id=?
            """,
            (int(user_id),),
        ).fetchone()
        missing_rows = cur.execute(
            f"""
                SELECT
                    COALESCE(CAST(s.nm_id AS TEXT),'') AS nm_id,
                    COALESCE(s.supplier_article,'') AS supplier_article,
                COALESCE(s.barcode,'') AS barcode,
                COUNT(*) AS quantity,
                ROUND(COALESCE(SUM(s.price_with_disc),0),2) AS revenue
            FROM sales s
            WHERE s.telegram_id=?
              AND substr(s.sale_date,1,10) BETWEEN ? AND ?
              AND COALESCE(s.is_return,0)=0
                  AND {cost_expr} <= 0
                GROUP BY COALESCE(CAST(s.nm_id AS TEXT),''), COALESCE(s.supplier_article,''), COALESCE(s.barcode,'')
                ORDER BY revenue DESC, quantity DESC
                LIMIT ?
                """,
                (int(user_id), str(date_from), str(date_to), int(limit)),
        ).fetchall()
        matched_stats = cur.execute(
            f"""
            SELECT
                COUNT(*) AS total_rows,
                SUM(
                    CASE
                        WHEN {cost_expr} > 0 THEN 1 ELSE 0 END
                ) AS matched_rows
            FROM sales s
            WHERE s.telegram_id=?
              AND substr(s.sale_date,1,10) BETWEEN ? AND ?
            """,
            (int(user_id), str(date_from), str(date_to)),
        ).fetchone()
        matching_breakdown = cur.execute(
            """
            SELECT
                COUNT(*) AS total_sales_rows,
                SUM(
                    CASE
                        WHEN EXISTS(
                            SELECT 1
                            FROM product_catalog pc
                            WHERE pc.user_id=s.telegram_id
                              AND s.nm_id IS NOT NULL
                              AND pc.nm_id=s.nm_id
                              AND COALESCE(pc.cost_price,0)>0
                        ) THEN 1 ELSE 0 END
                ) AS matched_by_nm_id,
                SUM(
                    CASE
                        WHEN NOT EXISTS(
                            SELECT 1
                            FROM product_catalog pc
                            WHERE pc.user_id=s.telegram_id
                              AND s.nm_id IS NOT NULL
                              AND pc.nm_id=s.nm_id
                              AND COALESCE(pc.cost_price,0)>0
                        )
                        AND EXISTS(
                            SELECT 1
                            FROM product_catalog pc
                            WHERE pc.user_id=s.telegram_id
                              AND TRIM(COALESCE(s.supplier_article,''))!=''
                              AND pc.supplier_article=s.supplier_article
                              AND COALESCE(pc.cost_price,0)>0
                        ) THEN 1 ELSE 0 END
                ) AS matched_by_supplier_article,
                SUM(
                    CASE
                        WHEN NOT EXISTS(
                            SELECT 1
                            FROM product_catalog pc
                            WHERE pc.user_id=s.telegram_id
                              AND s.nm_id IS NOT NULL
                              AND pc.nm_id=s.nm_id
                              AND COALESCE(pc.cost_price,0)>0
                        )
                        AND NOT EXISTS(
                            SELECT 1
                            FROM product_catalog pc
                            WHERE pc.user_id=s.telegram_id
                              AND TRIM(COALESCE(s.supplier_article,''))!=''
                              AND pc.supplier_article=s.supplier_article
                              AND COALESCE(pc.cost_price,0)>0
                        )
                        AND EXISTS(
                            SELECT 1
                            FROM product_catalog pc
                            WHERE pc.user_id=s.telegram_id
                              AND TRIM(COALESCE(s.barcode,''))!=''
                              AND pc.barcode=s.barcode
                              AND COALESCE(pc.cost_price,0)>0
                        ) THEN 1 ELSE 0 END
                ) AS matched_by_barcode,
                SUM(
                    CASE
                        WHEN NOT EXISTS(
                            SELECT 1
                            FROM product_catalog pc
                            WHERE pc.user_id=s.telegram_id
                              AND s.nm_id IS NOT NULL
                              AND pc.nm_id=s.nm_id
                              AND COALESCE(pc.cost_price,0)>0
                        )
                        AND NOT EXISTS(
                            SELECT 1
                            FROM product_catalog pc
                            WHERE pc.user_id=s.telegram_id
                              AND TRIM(COALESCE(s.supplier_article,''))!=''
                              AND pc.supplier_article=s.supplier_article
                              AND COALESCE(pc.cost_price,0)>0
                        )
                        AND NOT EXISTS(
                            SELECT 1
                            FROM product_catalog pc
                            WHERE pc.user_id=s.telegram_id
                              AND TRIM(COALESCE(s.barcode,''))!=''
                              AND pc.barcode=s.barcode
                              AND COALESCE(pc.cost_price,0)>0
                        )
                        AND EXISTS(
                            SELECT 1
                            FROM products p
                            WHERE p.telegram_id IN (s.telegram_id, 0)
                              AND TRIM(COALESCE(s.supplier_article,''))!=''
                              AND p.supplier_article=s.supplier_article
                              AND COALESCE(p.cost_price,0)>0
                        ) THEN 1 ELSE 0 END
                ) AS matched_by_legacy_fallback
            FROM sales s
            WHERE s.telegram_id=?
              AND substr(s.sale_date,1,10) BETWEEN ? AND ?
            """,
            (int(user_id), str(date_from), str(date_to)),
        ).fetchone()
        legacy_products = cur.execute(
            """
            SELECT
                COUNT(*) AS rows_count,
                SUM(CASE WHEN COALESCE(cost_price,0)>0 THEN 1 ELSE 0 END) AS rows_with_cost
            FROM products
            WHERE telegram_id IN (?,0)
            """,
            (int(user_id),),
        ).fetchone()
        total_rows = int((matched_stats["total_rows"] or 0) if matched_stats else 0)
        matched_rows = int((matched_stats["matched_rows"] or 0) if matched_stats else 0)
        return {
            "user_id": int(user_id),
            "period": f"{date_from}..{date_to}",
            "catalog_rows": int((catalog["catalog_rows"] or 0) if catalog else 0),
            "rows_with_cost": int((catalog["rows_with_cost"] or 0) if catalog else 0),
            "rows_without_cost": int((catalog["rows_without_cost"] or 0) if catalog else 0),
            "sales_rows": total_rows,
            "matched_sales_rows": matched_rows,
            "coverage_percent": round((matched_rows / total_rows) * 100.0, 1) if total_rows else 0.0,
            "matched_by_nm_id": int((matching_breakdown["matched_by_nm_id"] or 0) if matching_breakdown else 0),
            "matched_by_supplier_article": int((matching_breakdown["matched_by_supplier_article"] or 0) if matching_breakdown else 0),
            "matched_by_barcode": int((matching_breakdown["matched_by_barcode"] or 0) if matching_breakdown else 0),
            "matched_by_legacy_fallback": int((matching_breakdown["matched_by_legacy_fallback"] or 0) if matching_breakdown else 0),
            "missing_cost_skus": len(missing_rows),
            "top_missing_cost": [dict(row) for row in missing_rows],
            "legacy_products_rows": int((legacy_products["rows_count"] or 0) if legacy_products else 0),
            "legacy_products_rows_with_cost": int((legacy_products["rows_with_cost"] or 0) if legacy_products else 0),
        }
    finally:
        conn.close()
