from __future__ import annotations

import asyncio
import sqlite3
from types import SimpleNamespace

import config
import db_manager
import product_catalog
import telegram_bot


def _prepare_db(tmp_path):
    db_path = str(tmp_path / "cost-commands.sqlite")
    config.DB_NAME = db_path
    db_manager.DB_NAME = db_path
    product_catalog.DB_NAME = db_path
    telegram_bot.DB_NAME = db_path
    db_manager.init_db()
    return db_path


def _run(coro):
    return asyncio.run(coro)


def _build_update(user_id, replies):
    async def _reply_text(text, **kwargs):
        replies.append(str(text))

    return SimpleNamespace(
        effective_user=SimpleNamespace(id=user_id),
        message=SimpleNamespace(reply_text=_reply_text),
    )


def test_cost_command_missing_set_and_list(tmp_path, monkeypatch):
    db_path = _prepare_db(tmp_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("INSERT INTO users(telegram_id, username, tariff, is_active) VALUES(42, 'u', 'PRO', 1)")
        conn.execute(
            "INSERT INTO sales(sale_id, telegram_id, sale_date, supplier_article, nm_id, barcode, total_price, for_pay, finished_price, price_with_disc, is_return) VALUES('sale-1', 42, '2026-05-10', 'OZ-1', 531885568, 'BC-1', 7095, 6000, 7095, 7095, 0)"
        )
        conn.execute(
            "INSERT INTO sales(sale_id, telegram_id, sale_date, supplier_article, nm_id, barcode, total_price, for_pay, finished_price, price_with_disc, is_return) VALUES('sale-2', 42, '2026-05-11', 'OZ-1', 531885568, 'BC-1', 1000, 800, 1000, 1000, 0)"
        )
        conn.execute(
            "INSERT INTO sales(sale_id, telegram_id, sale_date, supplier_article, nm_id, barcode, total_price, for_pay, finished_price, price_with_disc, is_return) VALUES('sale-3', 42, '2026-05-12', 'OZ-2', 531885569, 'BC-2', 1200, 900, 1200, 1200, 0)"
        )
        conn.commit()
    finally:
        conn.close()

    product_catalog.sync_product_catalog(42, period=("2026-05-01", "2026-05-31"))

    outputs: list[str] = []

    async def _access(*_args, **_kwargs):
        return True

    async def _send_long(_update, text, **_kwargs):
        outputs.append(str(text))

    monkeypatch.setattr(telegram_bot, "access", _access)
    monkeypatch.setattr(telegram_bot, "send_long", _send_long)

    update = _build_update(42, outputs)

    _run(telegram_bot.cost_command(update, SimpleNamespace(args=["missing", "2026-05-01", "2026-05-31"])))
    assert any("OZ-1" in text for text in outputs)
    assert any("причина: себестоимость не заполнена" in text for text in outputs)

    outputs.clear()
    _run(telegram_bot.cost_command(update, SimpleNamespace(args=["set", "531885568", "120"])))
    assert any("120.00" in text for text in outputs)

    matched = product_catalog.match_product(42, nm_id=531885568)
    assert matched is not None
    assert float(matched["cost_price"]) == 120.0

    outputs.clear()
    _run(telegram_bot.cost_command(update, SimpleNamespace(args=["list"])))
    assert any("Себестоимость по каталогу" in text for text in outputs)
    assert any("OZ-1: 120.00" in text for text in outputs)
