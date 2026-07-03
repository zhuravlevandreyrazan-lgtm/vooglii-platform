from __future__ import annotations

import sqlite3

from config import DB_NAME
from db_manager import init_db
from user_manager import clear_user_token, get_user, get_user_token, save_user
from security.token_crypto import validate_wb_token


def _bot():
    try:
        import telegram_bot
        return telegram_bot
    except Exception:
        return None


def is_wb_connected(user_id):
    bot = _bot()
    token = bot.get_user_token(user_id) if bot and hasattr(bot, "get_user_token") else get_user_token(user_id)
    return bool(token)


def get_account_status(user_id):
    bot = _bot()
    user_row = bot.get_user(user_id) if bot and hasattr(bot, "get_user") else get_user(user_id)
    return {
        "connected": bool(user_row and user_row[2]),
        "user_row": user_row,
    }


def connect_wb_account(user_id, username, token):
    validated = validate_wb_token(str(token or "").strip())
    bot = _bot()
    if bot and hasattr(bot, "save_user"):
        bot.save_user(user_id, username, validated)
    else:
        save_user(user_id, username, validated)

    init_db()
    conn = sqlite3.connect(DB_NAME)
    try:
        cur = conn.cursor()
        cur.execute(
            '''
            INSERT OR IGNORE INTO notifications(
                telegram_id,daily_enabled,daily_hour,weekly_enabled,low_stock_threshold,negative_profit_alert,drr_alert_threshold,sales_drop_threshold
            ) VALUES(?,?,?,?,?,?,?,?)
            ''',
            (user_id, 1, 9, 1, 5, 1, 30, 40),
        )
        conn.commit()
    finally:
        conn.close()
    return {"connected": True}


def disconnect_wb_account(user_id):
    bot = _bot()
    if bot and hasattr(bot, "clear_user_token"):
        bot.clear_user_token(user_id)
    else:
        clear_user_token(user_id)
    return {"connected": False}
