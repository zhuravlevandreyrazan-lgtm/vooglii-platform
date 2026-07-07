import logging
import sqlite3
import time
from config import DB_NAME

logger = logging.getLogger(__name__)


def _is_readonly_db_error(exc):
    return isinstance(exc, sqlite3.OperationalError) and 'readonly database' in str(exc or '').lower()


def get_conn():
    conn = sqlite3.connect(DB_NAME, timeout=5)
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA journal_mode = WAL')
    conn.execute('PRAGMA busy_timeout = 5000')
    conn.execute('PRAGMA synchronous = NORMAL')
    return conn


def execute_with_retry(operation, retries=3, delay_seconds=0.2):
    last_exc = None
    for attempt in range(retries):
        try:
            return operation()
        except sqlite3.OperationalError as exc:
            last_exc = exc
            if 'locked' not in str(exc or '').lower() or attempt >= retries - 1:
                raise
            time.sleep(delay_seconds * (attempt + 1))
    if last_exc is not None:
        raise last_exc


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
        cur.execute('''CREATE TABLE IF NOT EXISTS product_catalog(
        user_id INTEGER NOT NULL,
        nm_id INTEGER NOT NULL,
        supplier_article TEXT,
        barcode TEXT,
        brand TEXT,
        subject TEXT,
        tech_size TEXT,
        name TEXT,
        cost_price REAL DEFAULT 0,
        last_price REAL DEFAULT 0,
        source TEXT,
        created_at TEXT,
        updated_at TEXT,
        PRIMARY KEY(user_id, nm_id)
        )''')

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
        cur.execute('''CREATE TABLE IF NOT EXISTS advert_sku_links(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER NOT NULL,
        advert_id TEXT NOT NULL,
        advert_date TEXT,
        campaign_name TEXT,
        nm_id INTEGER,
        subject_id TEXT,
        sku_name TEXT,
        supplier_article TEXT,
        source TEXT,
        confidence TEXT,
        last_seen_at TEXT,
        UNIQUE(telegram_id, advert_id, advert_date, supplier_article, nm_id, source)
        )''')
        for c, s in {
            'advert_date': 'TEXT',
            'campaign_name': 'TEXT',
            'nm_id': 'INTEGER',
            'subject_id': 'TEXT',
            'sku_name': 'TEXT',
            'supplier_article': 'TEXT',
            'source': 'TEXT',
            'confidence': 'TEXT',
            'last_seen_at': 'TEXT',
        }.items():
            _add(cur, 'advert_sku_links', c, s)

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
        cur.execute('''CREATE TABLE IF NOT EXISTS runtime_health(
        component TEXT PRIMARY KEY,
        status TEXT,
        last_heartbeat TEXT,
        details TEXT
        )''')
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
        cur.execute('''CREATE TABLE IF NOT EXISTS sync_state(
        telegram_id INTEGER NOT NULL,
        sync_block TEXT NOT NULL,
        status TEXT NOT NULL,
        status_reason TEXT,
        last_success_at TEXT,
        next_allowed_at TEXT,
        rows_inserted INTEGER DEFAULT 0,
        rows_updated INTEGER DEFAULT 0,
        rows_skipped INTEGER DEFAULT 0,
        rows_invalid INTEGER DEFAULT 0,
        source_rows INTEGER DEFAULT 0,
        source_name TEXT,
        updated_at TEXT NOT NULL,
        meta_json TEXT,
        PRIMARY KEY(telegram_id, sync_block)
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS finance_expense_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        event_date TEXT NOT NULL,
        period_key TEXT,
        source_event_id TEXT,
        source_table TEXT,
        source_type TEXT,
        expense_category TEXT NOT NULL,
        amount REAL NOT NULL DEFAULT 0,
        currency TEXT DEFAULT 'RUB',
        nm_id TEXT,
        supplier_article TEXT,
        finance_status TEXT,
        raw_payload_json TEXT,
        created_at TEXT,
        updated_at TEXT
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS stock_snapshots(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        snapshot_date TEXT NOT NULL,
        period_key TEXT,
        source_snapshot_id TEXT,
        source_type TEXT,
        supplier_article TEXT,
        nm_id TEXT,
        barcode TEXT,
        warehouse_name TEXT,
        quantity INTEGER DEFAULT 0,
        quantity_full INTEGER DEFAULT 0,
        in_way_to_client INTEGER DEFAULT 0,
        in_way_from_client INTEGER DEFAULT 0,
        is_historical_available INTEGER DEFAULT 1,
        raw_payload_json TEXT,
        created_at TEXT,
        updated_at TEXT
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS financial_snapshot_audit(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        period_start TEXT NOT NULL,
        period_end TEXT NOT NULL,
        period_key TEXT,
        snapshot_key TEXT,
        finance_status TEXT,
        finance_confidence TEXT,
        profit_display_mode TEXT,
        revenue REAL DEFAULT 0,
        expenses_total REAL DEFAULT 0,
        net_profit REAL DEFAULT 0,
        source_map_json TEXT,
        warnings_json TEXT,
        snapshot_json TEXT,
        created_at TEXT,
        updated_at TEXT
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS sync_locks(
        telegram_id INTEGER NOT NULL,
        sync_block TEXT NOT NULL,
        started_at TEXT NOT NULL,
        PRIMARY KEY(telegram_id, sync_block)
    )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS sync_queue(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        block TEXT NOT NULL,
        period_from TEXT NOT NULL,
        period_to TEXT NOT NULL,
        status TEXT NOT NULL,
        priority INTEGER DEFAULT 100,
        run_after TEXT,
        attempts INTEGER DEFAULT 0,
        last_error TEXT,
        created_at TEXT,
        updated_at TEXT
    )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS sync_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        block TEXT NOT NULL,
        status TEXT NOT NULL,
        source_rows INTEGER DEFAULT 0,
        retry_at TEXT,
        message TEXT,
        created_at TEXT
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

        cur.execute('''CREATE TABLE IF NOT EXISTS organizations(
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        plan TEXT DEFAULT 'starter',
        status TEXT DEFAULT 'active',
        created_at TEXT,
        updated_at TEXT
        )''')

        cur.execute('''CREATE TABLE IF NOT EXISTS workspace_state(
        state_key TEXT PRIMARY KEY,
        organization_id TEXT,
        cabinet_id TEXT,
        last_changed TEXT
        )''')

        cur.execute('''CREATE TABLE IF NOT EXISTS wb_cabinets(
        id TEXT PRIMARY KEY,
        organization_id TEXT NOT NULL,
        data_owner_id INTEGER UNIQUE NOT NULL,
        name TEXT NOT NULL,
        seller_id TEXT,
        seller_token_encrypted TEXT,
        seller_token_masked TEXT,
        statistics_token_encrypted TEXT,
        statistics_token_masked TEXT,
        advertising_token_encrypted TEXT,
        advertising_token_masked TEXT,
        finance_token_encrypted TEXT,
        finance_token_masked TEXT,
        status TEXT DEFAULT 'disconnected',
        scopes TEXT,
        connected INTEGER DEFAULT 0,
        data_quality TEXT DEFAULT 'pending',
        last_sync_status TEXT,
        sync_message TEXT,
        created_at TEXT,
        updated_at TEXT,
        last_checked_at TEXT,
        last_sync_at TEXT
        )''')
        for c,s in {
        'seller_id':'TEXT',
        'seller_token_encrypted':'TEXT',
        'seller_token_masked':'TEXT',
        'statistics_token_encrypted':'TEXT',
        'statistics_token_masked':'TEXT',
        'advertising_token_encrypted':'TEXT',
        'advertising_token_masked':'TEXT',
        'finance_token_encrypted':'TEXT',
        'finance_token_masked':'TEXT',
        'status':"TEXT DEFAULT 'disconnected'",
        'scopes':'TEXT',
        'connected':'INTEGER DEFAULT 0',
        'data_quality':"TEXT DEFAULT 'pending'",
        'last_sync_status':'TEXT',
        'sync_message':'TEXT',
        'created_at':'TEXT',
        'updated_at':'TEXT',
        'last_checked_at':'TEXT',
        'last_sync_at':'TEXT'
        }.items(): _add(cur,'wb_cabinets',c,s)

        cur.execute('''CREATE TABLE IF NOT EXISTS wb_sync_jobs(
        id TEXT PRIMARY KEY,
        cabinet_id TEXT NOT NULL,
        type TEXT NOT NULL,
        status TEXT NOT NULL,
        started_at TEXT,
        finished_at TEXT,
        duration_ms INTEGER,
        records_loaded INTEGER DEFAULT 0,
        error_message TEXT,
        runtime_source TEXT,
        meta_json TEXT
        )''')
        for c,s in {
        'records_loaded':'INTEGER DEFAULT 0',
        'error_message':'TEXT',
        'runtime_source':'TEXT',
        'meta_json':'TEXT'
        }.items(): _add(cur,'wb_sync_jobs',c,s)

        cur.execute('''CREATE TABLE IF NOT EXISTS wb_api_health(
        cabinet_id TEXT NOT NULL,
        section TEXT NOT NULL,
        status TEXT,
        last_success_at TEXT,
        last_error_at TEXT,
        last_error_message TEXT,
        rate_limit_state TEXT,
        message TEXT,
        required_action TEXT,
        PRIMARY KEY(cabinet_id, section)
        )''')
        for c,s in {
        'message':'TEXT',
        'required_action':'TEXT'
        }.items(): _add(cur,'wb_api_health',c,s)

        cur.execute('''CREATE TABLE IF NOT EXISTS wb_sync_schedules(
        id TEXT PRIMARY KEY,
        cabinet_id TEXT NOT NULL,
        sync_type TEXT NOT NULL,
        enabled INTEGER DEFAULT 1,
        interval_minutes INTEGER DEFAULT 60,
        status TEXT DEFAULT 'healthy',
        last_run_at TEXT,
        next_run_at TEXT,
        created_at TEXT,
        updated_at TEXT
        )''')
        for c,s in {
        'enabled':'INTEGER DEFAULT 1',
        'interval_minutes':'INTEGER DEFAULT 60',
        'status':"TEXT DEFAULT 'healthy'",
        'last_run_at':'TEXT',
        'next_run_at':'TEXT',
        'created_at':'TEXT',
        'updated_at':'TEXT'
        }.items(): _add(cur,'wb_sync_schedules',c,s)

        for name, table, cols in [('idx_sales_user_date','sales','telegram_id,sale_date'),('idx_orders_user_date','orders','telegram_id,order_date'),('idx_exp_user_date','expenses','telegram_id,expense_date'),('idx_ads_user_date','advertising','telegram_id,advert_date'),('idx_stocks_user','stocks','telegram_id,supplier_article'),('idx_finance_raw_user_rrd','finance_raw_audit','telegram_id,rrd_id'),('idx_finance_raw_user_date','finance_raw_audit','telegram_id,report_date')]:
            cur.execute(f'CREATE INDEX IF NOT EXISTS {name} ON {table} ({cols})')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_sync_state_user_block_updated ON sync_state (telegram_id, sync_block, updated_at)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_product_catalog_user_article ON product_catalog (user_id, supplier_article)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_product_catalog_user_barcode ON product_catalog (user_id, barcode)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_finance_expense_events_user_date ON finance_expense_events (user_id, event_date)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_finance_expense_events_user_period ON finance_expense_events (user_id, period_key)')
        cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_finance_expense_events_source_id ON finance_expense_events (user_id, source_event_id) WHERE source_event_id IS NOT NULL')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_stock_snapshots_user_date ON stock_snapshots (user_id, snapshot_date)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_stock_snapshots_user_period ON stock_snapshots (user_id, period_key)')
        cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_stock_snapshots_source_id ON stock_snapshots (user_id, source_snapshot_id) WHERE source_snapshot_id IS NOT NULL')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_financial_snapshot_audit_user_period ON financial_snapshot_audit (user_id, period_start, period_end)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_financial_snapshot_audit_user_period_key ON financial_snapshot_audit (user_id, period_key)')
        cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_financial_snapshot_audit_snapshot_key ON financial_snapshot_audit (user_id, snapshot_key) WHERE snapshot_key IS NOT NULL')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_sync_queue_ready ON sync_queue (status, run_after, priority)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_sync_queue_user_block ON sync_queue (user_id, block, period_from, period_to)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_sync_history_user_created ON sync_history (user_id, created_at)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_wb_sync_jobs_cabinet_started ON wb_sync_jobs (cabinet_id, started_at)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_wb_sync_schedules_cabinet_next_run ON wb_sync_schedules (cabinet_id, next_run_at)')
        cur.execute("INSERT OR IGNORE INTO organizations(id,name,plan,status,created_at,updated_at) VALUES('org_vooglii_main','VOOGLII Workspace','starter','active',datetime('now'),datetime('now'))")
        cur.execute("INSERT OR IGNORE INTO workspace_state(state_key,organization_id,cabinet_id,last_changed) VALUES('active','org_vooglii_main',NULL,datetime('now'))")
        conn.commit()
    except sqlite3.OperationalError as exc:
        if _is_readonly_db_error(exc):
            logger.warning('Skipping init_db schema writes due to readonly database: %s', exc)
        else:
            raise
    finally:
        conn.close()


def update_runtime_health(component, status, details=None):
    conn = get_conn()
    try:
        conn.execute(
            '''
            INSERT INTO runtime_health(component,status,last_heartbeat,details)
            VALUES(?,?,datetime('now'),?)
            ON CONFLICT(component) DO UPDATE SET
                status=excluded.status,
                last_heartbeat=excluded.last_heartbeat,
                details=excluded.details
            ''',
            (str(component or ''), str(status or ''), str(details or '')),
        )
        conn.commit()
    finally:
        conn.close()


def get_runtime_health(component):
    conn = get_conn()
    try:
        row = conn.execute(
            'SELECT component,status,last_heartbeat,details FROM runtime_health WHERE component=?',
            (str(component or ''),),
        ).fetchone()
        if not row:
            return None
        return {
            'component': row[0],
            'status': row[1],
            'last_heartbeat': row[2],
            'details': row[3],
        }
    finally:
        conn.close()

if __name__ == '__main__':
    init_db(); print('База данных проверена/создана.')
