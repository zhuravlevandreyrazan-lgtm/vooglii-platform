import sqlite3
from datetime import datetime
from config import DB_NAME
from db_manager import init_db


def save_update(status, sales_loaded=0, telegram_id=None, orders_loaded=0, expenses_loaded=0, ads_loaded=0, stocks_loaded=0):
    init_db(); conn=sqlite3.connect(DB_NAME); cur=conn.cursor()
    cur.execute('''INSERT INTO updates(telegram_id,update_time,status,sales_loaded,orders_loaded,expenses_loaded,ads_loaded,stocks_loaded) VALUES(?,?,?,?,?,?,?,?)''',(telegram_id,datetime.now().strftime('%Y-%m-%d %H:%M:%S'),status,sales_loaded,orders_loaded,expenses_loaded,ads_loaded,stocks_loaded))
    conn.commit(); conn.close()

def get_last_update(telegram_id=None):
    init_db(); conn=sqlite3.connect(DB_NAME); cur=conn.cursor()
    if telegram_id is None:
        cur.execute('SELECT update_time,status,sales_loaded,orders_loaded,expenses_loaded,ads_loaded,stocks_loaded FROM updates ORDER BY id DESC LIMIT 1')
    else:
        cur.execute('SELECT update_time,status,sales_loaded,orders_loaded,expenses_loaded,ads_loaded,stocks_loaded FROM updates WHERE telegram_id=? ORDER BY id DESC LIMIT 1',(telegram_id,))
    row=cur.fetchone(); conn.close(); return row
