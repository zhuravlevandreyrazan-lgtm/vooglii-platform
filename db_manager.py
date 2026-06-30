import logging
import sqlite3
from config import DB_NAME

logger = logging.getLogger(__name__)


def _is_readonly_db_error(exc):
    return isinstance(exc, sqlite3.OperationalError) and 'readonly database' in str(exc or '').lower()


def get_conn():
    conn = sqlite3.connect(DB_NAME)
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def _col(cur, table, col):
    cur.execute(f'PRAGMA table_info({table})')
    return any(r[1] == col for r in cur.fetchall())


def _add(cur, table, col, spec):
    if not _col(cur, table, col):
        cur.execute(f'ALTER TABLE {table} ADD COLUMN {col} {spec}')


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute('''CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id INTEGER UNIQUE, username TEXT,
        wb_token TEXT, tariff TEXT DEFAULT 'FREE', is_active INTEGER DEFAULT 1,
        role TEXT DEFAULT 'owner', subscription_until TEXT, referral_code TEXT UNIQUE,
        referred_by INTEGER, created_at TEXT, updated_at TEXT)''')
        for c,s in {'tariff':"TEXT DEFAULT 'FREE'",'is_active':'INTEGER DEFAULT 1','role':"TEXT DEFAULT 'owner'",'subscription_until':'TEXT','referral_code':'TEXT','referred_by':'INTEGER','created_at':'TEXT','updated_at':'TEXT','wb_token':'TEXT'}.items(): _add(cur,'users',c,s)

        cur.execute('''CREATE TABLE IF NOT EXISTS sales(
        sale_id TEXT PRIMARY KEY, telegram_id INTEGER, sale_date TEXT, supplier_article TEXT,
        nm_id INTEGER, barcode TEXT, warehouse_name TEXT, category TEXT, brand TEXT,
        total_price REAL DEFAULT 0, for_pay REAL DEFAULT 0, finished_price REAL DEFAULT 0,
        price_with_disc REAL DEFAULT 0, is_return INTEGER DEFAULT 0)''')
        for c,s in {'telegram_id':'INTEGER','brand':'TEXT','is_return':'INTEGER DEFAULT 0','total_price':'REAL DEFAULT 0','for_pay':'REAL DEFAULT 0','finished_price':'REAL DEFAULT 0','price_with_disc':'REAL DEFAULT 0'}.items(): _add(cur,'sales',c,s)

        cur.execute('''CREATE TABLE IF NOT EXISTS orders(
        order_id TEXT PRIMARY KEY, telegram_id INTEGER, order_date TEXT, supplier_article TEXT,
        nm_id INTEGER, barcode TEXT, warehouse_name TEXT, category TEXT, brand TEXT,
        total_price REAL DEFAULT 0, finished_price REAL DEFAULT 0, price_with_disc REAL DEFAULT 0,
        is_cancel INTEGER DEFAULT 0, cancel_date TEXT)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS products(
        telegram_id INTEGER DEFAULT 0, supplier_article TEXT, cost_price REAL DEFAULT 0,
        last_price REAL DEFAULT 0, PRIMARY KEY(telegram_id, supplier_article))''')
        for c,s in {'telegram_id':'INTEGER DEFAULT 0','last_price':'REAL DEFAULT 0'}.items():
            try: _add(cur,'products',c,s)
            except sqlite3.OperationalError: pass

        cur.execute('''CREATE TABLE IF NOT EXISTS expenses(
        id INTEGER PRIMARY KEY AUTOINCREMENT, unique_key TEXT UNIQUE, telegram_id INTEGER NOT NULL,
        expense_date TEXT NOT NULL, expense_type TEXT NOT NULL, amount REAL NOT NULL DEFAULT 0,
        supplier_article TEXT, comment TEXT, source TEXT DEFAULT 'manual', created_at TEXT)''')
        for c,s in {'unique_key':'TEXT UNIQUE','source':"TEXT DEFAULT 'manual'"}.items(): _add(cur,'expenses',c,s)
        cur.execute('''CREATE TABLE IF NOT EXISTS finance_raw_audit(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER NOT NULL,
        rrd_id TEXT NOT NULL,
        report_date TEXT,
        penalty REAL DEFAULT 0,
        deduction REAL DEFAULT 0,
        acceptance REAL DEFAULT 0,
        acceptance_fee REAL DEFAULT 0,
        additional_payment REAL DEFAULT 0,
        acquiring_fee REAL DEFAULT 0,
        nm_id TEXT,
        supplier_article TEXT,
        srid TEXT,
        doc_type_name TEXT,
        operation_type TEXT,
        payment_type TEXT,
        subject_name TEXT,
        brand_name TEXT,
        sa_name TEXT,
        bonus_type_name TEXT,
        sticker_id TEXT,
        gi_id TEXT,
        raw_json TEXT,
        created_at TEXT
    )''')
        for c, s in {
        'nm_id': 'TEXT',
        'supplier_article': 'TEXT',
        'srid': 'TEXT',
        'doc_type_name': 'TEXT',
        'operation_type': 'TEXT',
        'payment_type': 'TEXT',
        'subject_name': 'TEXT',
        'brand_name': 'TEXT',
        'sa_name': 'TEXT',
        'bonus_type_name': 'TEXT',
        'sticker_id': 'TEXT',
        'gi_id': 'TEXT',
        }.items():
            _add(cur, 'finance_raw_audit', c, s)

        cur.execute('''CREATE TABLE IF NOT EXISTS advertising(
        id INTEGER PRIMARY KEY AUTOINCREMENT, unique_key TEXT UNIQUE, telegram_id INTEGER,
        advert_date TEXT, campaign_id TEXT, campaign_name TEXT, supplier_article TEXT, nm_id INTEGER,
        app_type TEXT, name TEXT,
        views INTEGER DEFAULT 0, clicks INTEGER DEFAULT 0, orders INTEGER DEFAULT 0,
        sum_price REAL DEFAULT 0, spend REAL DEFAULT 0, ctr REAL DEFAULT 0, cpc REAL DEFAULT 0, cr REAL DEFAULT 0)''')
        for c, s in {'app_type': 'TEXT', 'name': 'TEXT'}.items():
            _add(cur, 'advertising', c, s)

        cur.execute('''CREATE TABLE IF NOT EXISTS stocks(
        id INTEGER PRIMARY KEY AUTOINCREMENT, unique_key TEXT UNIQUE, telegram_id INTEGER, stock_date TEXT,
        supplier_article TEXT, nm_id INTEGER, barcode TEXT, warehouse_name TEXT, quantity INTEGER DEFAULT 0,
        quantity_full INTEGER DEFAULT 0, in_way_to_client INTEGER DEFAULT 0, in_way_from_client INTEGER DEFAULT 0)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS updates(
        id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id INTEGER, update_time TEXT, status TEXT,
        sales_loaded INTEGER DEFAULT 0, orders_loaded INTEGER DEFAULT 0, expenses_loaded INTEGER DEFAULT 0,
        ads_loaded INTEGER DEFAULT 0, stocks_loaded INTEGER DEFAULT 0)''')
        for c,s in {'orders_loaded':'INTEGER DEFAULT 0','expenses_loaded':'INTEGER DEFAULT 0','ads_loaded':'INTEGER DEFAULT 0','stocks_loaded':'INTEGER DEFAULT 0','telegram_id':'INTEGER'}.items(): _add(cur,'updates',c,s)

        cur.execute('''CREATE TABLE IF NOT EXISTS plans(id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id INTEGER, plan_period TEXT, revenue_plan REAL DEFAULT 0, profit_plan REAL DEFAULT 0, orders_plan INTEGER DEFAULT 0, created_at TEXT)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS notifications(
        telegram_id INTEGER PRIMARY KEY,
        daily_enabled INTEGER DEFAULT 0,
        daily_hour INTEGER DEFAULT 9,
        weekly_enabled INTEGER DEFAULT 1,
        low_stock_threshold INTEGER DEFAULT 5,
        negative_profit_alert INTEGER DEFAULT 1,
        drr_alert_threshold REAL DEFAULT 30,
        sales_drop_threshold REAL DEFAULT 40
        )''')
        for c,s in {'weekly_enabled':'INTEGER DEFAULT 1','drr_alert_threshold':'REAL DEFAULT 30','sales_drop_threshold':'REAL DEFAULT 40'}.items(): _add(cur,'notifications',c,s)
        cur.execute('''CREATE TABLE IF NOT EXISTS referrals(id INTEGER PRIMARY KEY AUTOINCREMENT, referrer_id INTEGER, invited_id INTEGER UNIQUE, bonus_days INTEGER DEFAULT 30, created_at TEXT)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS price_history(id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id INTEGER, event_date TEXT, supplier_article TEXT, price REAL, cost_price REAL, source TEXT)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS audit_log(id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id INTEGER, event_time TEXT, action TEXT, details TEXT)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS competitors(id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id INTEGER, nm_id TEXT, name TEXT, price REAL, rating REAL, reviews INTEGER, position INTEGER, checked_at TEXT)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS api_cooldowns(
        telegram_id INTEGER NOT NULL,
        api_block TEXT NOT NULL,
        retry_after TEXT,
        last_status TEXT,
        updated_at TEXT,
        PRIMARY KEY(telegram_id, api_block)
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS sync_status(
        telegram_id INTEGER NOT NULL,
        sync_block TEXT NOT NULL,
        last_success TEXT,
        last_error TEXT,
        last_status TEXT,
        updated_at TEXT,
        PRIMARY KEY(telegram_id, sync_block)
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS sync_locks(
        telegram_id INTEGER NOT NULL,
        sync_block TEXT NOT NULL,
        started_at TEXT NOT NULL,
        PRIMARY KEY(telegram_id, sync_block)
    )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS tax_settings(
        telegram_id INTEGER PRIMARY KEY,
        tax_mode TEXT DEFAULT 'none',
        tax_rate REAL DEFAULT 0,
        min_tax_enabled INTEGER DEFAULT 0,
        updated_at TEXT
    )''')
        for c,s in {'tax_mode':"TEXT DEFAULT 'none'",'tax_rate':'REAL DEFAULT 0','min_tax_enabled':'INTEGER DEFAULT 0','updated_at':'TEXT'}.items(): _add(cur,'tax_settings',c,s)
        cur.execute('''CREATE TABLE IF NOT EXISTS replenishment_settings(
        telegram_id INTEGER PRIMARY KEY,
        sales_window_days INTEGER DEFAULT 30,
        target_stock_days INTEGER DEFAULT 45,
        lead_time_days INTEGER DEFAULT 14,
        safety_stock_days INTEGER DEFAULT 7,
        min_order_qty INTEGER DEFAULT 0,
        updated_at TEXT
        )''')
        for c,s in {
        'sales_window_days':'INTEGER DEFAULT 30',
        'target_stock_days':'INTEGER DEFAULT 45',
        'lead_time_days':'INTEGER DEFAULT 14',
        'safety_stock_days':'INTEGER DEFAULT 7',
        'min_order_qty':'INTEGER DEFAULT 0',
        'updated_at':'TEXT'
        }.items(): _add(cur,'replenishment_settings',c,s)
        for name, table, cols in [('idx_sales_user_date','sales','telegram_id,sale_date'),('idx_orders_user_date','orders','telegram_id,order_date'),('idx_exp_user_date','expenses','telegram_id,expense_date'),('idx_ads_user_date','advertising','telegram_id,advert_date'),('idx_stocks_user','stocks','telegram_id,supplier_article'),('idx_finance_raw_user_rrd','finance_raw_audit','telegram_id,rrd_id'),('idx_finance_raw_user_date','finance_raw_audit','telegram_id,report_date')]:
            cur.execute(f'CREATE INDEX IF NOT EXISTS {name} ON {table} ({cols})')
        conn.commit()
    except sqlite3.OperationalError as exc:
        if _is_readonly_db_error(exc):
            logger.warning('Skipping init_db schema writes due to readonly database: %s', exc)
        else:
            raise
    finally:
        conn.close()

if __name__ == '__main__':
    init_db(); print('База данных проверена/создана.')
