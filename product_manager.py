import sqlite3
from datetime import datetime
from config import DB_NAME
from db_manager import init_db


def _conn(): init_db(); return sqlite3.connect(DB_NAME)

def set_cost_price(article, cost_price, telegram_id=None):
    conn=_conn(); cur=conn.cursor(); tid=telegram_id or 0
    old=None
    cur.execute('SELECT cost_price,last_price FROM products WHERE telegram_id=? AND supplier_article=?',(tid,article)); row=cur.fetchone()
    if row: old=row[0]
    cur.execute('''INSERT INTO products(telegram_id,supplier_article,cost_price) VALUES(?,?,?) ON CONFLICT(telegram_id,supplier_article) DO UPDATE SET cost_price=excluded.cost_price''',(tid,article,float(cost_price)))
    cur.execute('INSERT INTO price_history(telegram_id,event_date,supplier_article,price,cost_price,source) VALUES(?,?,?,?,?,?)',(tid,datetime.now().strftime('%Y-%m-%d %H:%M:%S'),article,0,float(cost_price),'setcost'))
    conn.commit(); conn.close()

def get_cost_price(article, telegram_id=None):
    conn=_conn(); cur=conn.cursor(); cur.execute('SELECT cost_price FROM products WHERE supplier_article=? AND telegram_id IN (?,0) ORDER BY telegram_id DESC LIMIT 1',(article,telegram_id or 0)); row=cur.fetchone(); conn.close(); return row[0] if row else None

def get_products(telegram_id=None):
    conn=_conn(); cur=conn.cursor(); cur.execute('''SELECT supplier_article, MAX(cost_price) FROM products WHERE telegram_id IN (?,0) GROUP BY supplier_article ORDER BY supplier_article''',(telegram_id or 0,)); rows=cur.fetchall(); conn.close(); return rows

def sync_products_from_sales(telegram_id=None):
    conn=_conn(); cur=conn.cursor(); tid=telegram_id or 0
    cur.execute('''INSERT OR IGNORE INTO products(telegram_id,supplier_article,cost_price,last_price) SELECT ?, supplier_article, 0, MAX(price_with_disc) FROM sales WHERE (?=0 OR telegram_id=?) AND supplier_article IS NOT NULL GROUP BY supplier_article''',(tid,tid,tid))
    conn.commit(); conn.close()
