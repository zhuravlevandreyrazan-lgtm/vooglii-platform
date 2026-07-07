import sqlite3
from datetime import datetime, timedelta
from math import ceil
from config import DB_NAME, FREE_HISTORY_DAYS
from db_manager import init_db
from product_catalog import get_cost_map as get_product_catalog_cost_map, get_cost_price as get_catalog_cost_price
from user_manager import is_pro

PERIODS={'today':1,'week':7,'month':30,'all':None}

def normalize_period(p):
    if isinstance(p, (list, tuple)):
        parts=[str(x or '').strip() for x in p if str(x or '').strip()]
        if len(parts) == 2:
            try:
                start_dt=datetime.strptime(parts[0], '%Y-%m-%d')
                end_dt=datetime.strptime(parts[1], '%Y-%m-%d')
            except Exception:
                raise ValueError('INVALID_PERIOD')
            if start_dt > end_dt:
                raise ValueError('INVALID_PERIOD')
            return (f'{parts[0]} — {parts[1]}', (parts[0], parts[1]))
        if len(parts) == 1:
            p=parts[0]
        elif not parts:
            p='all'
        else:
            raise ValueError('INVALID_PERIOD')
    p = str(p or 'all').lower().strip().rstrip('\\/').strip()
    if p in PERIODS:
        return (p, PERIODS[p])
    raise ValueError('INVALID_PERIOD')
def _conn(): init_db(); return sqlite3.connect(DB_NAME)
def _from(days): return (datetime.now()-timedelta(days=days-1)).strftime('%Y-%m-%d')
def _is_date_range(value):
    return isinstance(value, tuple) and len(value) == 2 and all(isinstance(x, str) for x in value)
def _range_days(value):
    if not _is_date_range(value):
        return value
    start_dt=datetime.strptime(value[0], '%Y-%m-%d')
    end_dt=datetime.strptime(value[1], '%Y-%m-%d')
    return max(1, (end_dt-start_dt).days+1)
def allowed_days(telegram_id, days):
    if _is_date_range(days):
        if is_pro(telegram_id):
            return days
        range_days=_range_days(days)
        if range_days <= FREE_HISTORY_DAYS:
            return days
        return (_from(FREE_HISTORY_DAYS), datetime.now().strftime('%Y-%m-%d'))
    if is_pro(telegram_id): return days
    return FREE_HISTORY_DAYS if days is None or days>FREE_HISTORY_DAYS else days

def _where(alias, telegram_id=None, days=None, date_col='sale_date'):
    parts=[]; params=[]
    if telegram_id is not None: parts.append(f'{alias}.telegram_id=?'); params.append(telegram_id)
    if days is not None:
        if _is_date_range(days):
            parts.append(f"substr({alias}.{date_col},1,10) BETWEEN ? AND ?"); params.extend([days[0], days[1]])
        elif days==1: parts.append(f"substr({alias}.{date_col},1,10)=date('now')")
        else: parts.append(f"substr({alias}.{date_col},1,10)>=?"); params.append(_from(days))
    return ('WHERE '+' AND '.join(parts) if parts else ''), params


def _catalog_cost_lookup_sql(alias='s'):
    return (
        "COALESCE(("
        "SELECT pc.cost_price FROM product_catalog pc "
        f"WHERE pc.user_id={alias}.telegram_id AND {alias}.nm_id IS NOT NULL AND pc.nm_id={alias}.nm_id "
        "ORDER BY pc.updated_at DESC LIMIT 1"
        "),("
        "SELECT pc.cost_price FROM product_catalog pc "
        f"WHERE pc.user_id={alias}.telegram_id AND TRIM(COALESCE({alias}.supplier_article,''))!='' AND pc.supplier_article={alias}.supplier_article "
        "ORDER BY pc.updated_at DESC LIMIT 1"
        "),("
        "SELECT pc.cost_price FROM product_catalog pc "
        f"WHERE pc.user_id={alias}.telegram_id AND TRIM(COALESCE({alias}.barcode,''))!='' AND pc.barcode={alias}.barcode "
        "ORDER BY pc.updated_at DESC LIMIT 1"
        "),("
        "SELECT p2.cost_price FROM products p2 "
        f"WHERE p2.supplier_article={alias}.supplier_article AND p2.telegram_id IN ({alias}.telegram_id,0) "
        "ORDER BY p2.telegram_id DESC LIMIT 1"
        "),0)"
    )

def add_expense(telegram_id, expense_type, amount, expense_date=None, supplier_article=None, comment=None, source='manual'):
    et={'логистика':'logistics','реклама':'advertising','хранение':'storage','прочее':'other','ads':'advertising','ad':'advertising'}.get(str(expense_type).lower(), str(expense_type).lower())
    if et not in ('logistics','advertising','storage','other'): et='other'
    expense_date=expense_date or datetime.now().strftime('%Y-%m-%d')
    conn=_conn(); cur=conn.cursor(); cur.execute('''INSERT INTO expenses(unique_key,telegram_id,expense_date,expense_type,amount,supplier_article,comment,source,created_at) VALUES(NULL,?,?,?,?,?,?,?,?)''',(telegram_id,expense_date,et,float(amount),supplier_article,comment,source,datetime.now().strftime('%Y-%m-%d %H:%M:%S'))); conn.commit(); conn.close()

def get_expenses_total(telegram_id=None, days=None, article=None):
    """Возвращает расходы: логистика, реклама, хранение, прочее, всего.

    Важно: реклама считается надежно даже если expense-записи не создались:
    берем максимум между expenses(advertising) и таблицей advertising.spend,
    чтобы не задвоить рекламу при успешной загрузке обоих источников.
    """
    days=allowed_days(telegram_id, days) if telegram_id else days
    conn=_conn(); cur=conn.cursor()

    q="""SELECT
        COALESCE(SUM(CASE WHEN expense_type='logistics' THEN amount ELSE 0 END),0),
        COALESCE(SUM(CASE WHEN expense_type='advertising' THEN amount ELSE 0 END),0),
        COALESCE(SUM(CASE WHEN expense_type='storage' THEN amount ELSE 0 END),0),
        COALESCE(SUM(CASE WHEN expense_type NOT IN ('logistics','advertising','storage') THEN amount ELSE 0 END),0)
        FROM expenses WHERE 1=1"""
    params=[]
    if telegram_id is not None:
        q+=' AND telegram_id=?'; params.append(telegram_id)
    if days is not None:
        if _is_date_range(days):
            q+=' AND substr(expense_date,1,10) BETWEEN ? AND ?'; params.extend([days[0], days[1]])
        elif days==1:
            q+=" AND substr(expense_date,1,10)=date('now')"
        else:
            q+=' AND substr(expense_date,1,10)>=?'; params.append(_from(days))
    if article:
        # Для товара берем только привязанные расходы. Общие расходы не размазываем на каждый товар,
        # иначе аналитика по товарам завышает расходы в несколько раз.
        q+=' AND supplier_article=?'; params.append(article)
    cur.execute(q,params)
    logistics, adv_from_expenses, storage, other = [float(x or 0) for x in cur.fetchone()]

    aq='SELECT COALESCE(SUM(spend),0) FROM advertising WHERE 1=1'
    aparams=[]
    if telegram_id is not None:
        aq+=' AND telegram_id=?'; aparams.append(telegram_id)
    if days is not None:
        if _is_date_range(days):
            aq+=' AND substr(advert_date,1,10) BETWEEN ? AND ?'; aparams.extend([days[0], days[1]])
        elif days==1:
            aq+=" AND substr(advert_date,1,10)=date('now')"
        else:
            aq+=' AND substr(advert_date,1,10)>=?'; aparams.append(_from(days))
    if article:
        aq+=' AND supplier_article=?'; aparams.append(article)
    cur.execute(aq,aparams)
    adv_from_ads=float(cur.fetchone()[0] or 0)
    conn.close()

    advertising=max(adv_from_expenses, adv_from_ads)
    total=logistics+advertising+storage+other
    return (round(logistics,2), round(advertising,2), round(storage,2), round(other,2), round(total,2))

def get_expenses_list(telegram_id, days=None, limit=40):
    days=allowed_days(telegram_id, days); conn=_conn(); cur=conn.cursor(); q='SELECT expense_date,expense_type,amount,supplier_article,comment,source FROM expenses WHERE telegram_id=?'; params=[telegram_id]
    if days is not None:
        if _is_date_range(days): q+=' AND substr(expense_date,1,10) BETWEEN ? AND ?'; params.extend([days[0], days[1]])
        elif days==1: q+=" AND substr(expense_date,1,10)=date('now')"
        else: q+=' AND substr(expense_date,1,10)>=?'; params.append(_from(days))
    q+=' ORDER BY expense_date DESC,id DESC LIMIT ?'; params.append(limit); cur.execute(q,params); rows=cur.fetchall(); conn.close(); return rows

def get_orders_stats(days=None, telegram_id=None):
    days=allowed_days(telegram_id, days) if telegram_id else days; conn=_conn(); cur=conn.cursor(); where,params=_where('o',telegram_id,days,'order_date')
    cur.execute(f'''SELECT COUNT(*),COALESCE(SUM(price_with_disc),0),COALESCE(SUM(CASE WHEN is_cancel=1 THEN 1 ELSE 0 END),0),COALESCE(SUM(CASE WHEN is_cancel=1 THEN price_with_disc ELSE 0 END),0) FROM orders o {where}''',params); row=cur.fetchone(); conn.close(); return row

def get_period_stats(days=None, telegram_id=None):
    days=allowed_days(telegram_id, days) if telegram_id else days; conn=_conn(); cur=conn.cursor(); where,params=_where('s',telegram_id,days); cur.execute(f'SELECT COUNT(*),COALESCE(SUM(for_pay),0) FROM sales s {where}',params); row=cur.fetchone(); conn.close(); return row
get_total_stats=get_period_stats

def get_products_count(telegram_id=None): return get_products_count_period(None, telegram_id)
def get_products_count_period(days=None, telegram_id=None):
    days=allowed_days(telegram_id, days) if telegram_id else days; conn=_conn(); cur=conn.cursor(); where,params=_where('s',telegram_id,days); cur.execute(f'SELECT COUNT(DISTINCT supplier_article) FROM sales s {where}',params); row=cur.fetchone()[0]; conn.close(); return row

def get_profit_stats(days=None, telegram_id=None):
    days=allowed_days(telegram_id, days) if telegram_id else days; conn=_conn(); cur=conn.cursor(); where,params=_where('s',telegram_id,days); cost_sql=_catalog_cost_lookup_sql('s')
    cur.execute(f'''SELECT COALESCE(SUM(s.price_with_disc),0),COALESCE(SUM(s.for_pay),0),COALESCE(SUM({cost_sql}),0),COALESCE(SUM(CASE WHEN s.is_return=1 THEN 1 ELSE 0 END),0) FROM sales s {where}''',params)
    sales_sum,payout,cost,returns=cur.fetchone(); conn.close(); logi,adv,stor,other,exp=get_expenses_total(telegram_id,days); comm=sales_sum-payout; gross=payout-cost; net=gross-exp; margin=net/payout*100 if payout else 0
    return tuple([round(x,2) if isinstance(x,float) else x for x in (sales_sum,comm,payout,cost,logi,adv,stor,other,exp,gross,net,round(margin,1),int(returns or 0))])

def get_expense_reconciliation(days=None, telegram_id=None, other_visible_expenses=0.0):
    st=get_profit_stats(days, telegram_id)
    payout=float(st[2] or 0)
    cost=float(st[3] or 0)
    logistics=float(st[4] or 0)
    advertising=float(st[5] or 0)
    storage=float(st[6] or 0)
    other_visible=float(other_visible_expenses or 0)
    visible_expenses=round(cost+logistics+advertising+storage+other_visible, 2)
    calculated_profit_before_tax=round(payout-visible_expenses, 2)
    hidden_difference=round(calculated_profit_before_tax-float(st[10] or 0), 2)
    return {
        'visible_expenses': visible_expenses,
        'calculated_profit_before_tax': calculated_profit_before_tax,
        'hidden_difference': hidden_difference,
    }

def get_cost_fill_stats(days=None, telegram_id=None):
    days=allowed_days(telegram_id, days) if telegram_id else days; conn=_conn(); cur=conn.cursor(); where,params=_where('s',telegram_id,days); cost_sql=_catalog_cost_lookup_sql('s')
    cur.execute(f'''
    SELECT
      COUNT(*),
      COALESCE(SUM(CASE WHEN {cost_sql}>0 THEN 1 ELSE 0 END),0),
      COUNT(DISTINCT CASE WHEN {cost_sql}<=0 THEN COALESCE(NULLIF(s.supplier_article,''), CAST(s.nm_id AS TEXT), COALESCE(s.barcode,'')) END)
    FROM sales s {where}
    ''',params)
    total_rows,rows_with_cost,missing_articles=cur.fetchone(); conn.close()
    total_rows=int(total_rows or 0); rows_with_cost=int(rows_with_cost or 0); missing_articles=int(missing_articles or 0)
    return {
        'total_rows': total_rows,
        'rows_with_cost': rows_with_cost,
        'missing_articles': missing_articles,
        'all_missing': total_rows > 0 and rows_with_cost == 0,
        'partial_missing': total_rows > 0 and 0 < rows_with_cost < total_rows,
    }

def get_tax_settings(telegram_id):
    init_db(); conn=_conn(); cur=conn.cursor()
    cur.execute('SELECT tax_mode,tax_rate,min_tax_enabled,updated_at FROM tax_settings WHERE telegram_id=?',(telegram_id,))
    row=cur.fetchone(); conn.close()
    if not row:
        return {'telegram_id':telegram_id,'tax_mode':'none','tax_rate':0.0,'min_tax_enabled':0,'updated_at':None}
    return {'telegram_id':telegram_id,'tax_mode':str(row[0] or 'none'),'tax_rate':float(row[1] or 0),'min_tax_enabled':int(row[2] or 0),'updated_at':row[3]}

def set_tax_settings(telegram_id, tax_mode, tax_rate, min_tax_enabled=0):
    mode=str(tax_mode or 'none').strip().lower()
    if mode not in ('none','usn_income','usn_profit','npd','custom'):
        raise ValueError('INVALID_TAX_MODE')
    rate=float(tax_rate or 0)
    if rate < 0 or rate > 100:
        raise ValueError('Ставка налога должна быть от 0 до 100%')
    now=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn=_conn(); cur=conn.cursor()
    cur.execute('''
    INSERT INTO tax_settings(telegram_id,tax_mode,tax_rate,min_tax_enabled,updated_at)
    VALUES(?,?,?,?,?)
    ON CONFLICT(telegram_id) DO UPDATE SET
      tax_mode=excluded.tax_mode,
      tax_rate=excluded.tax_rate,
      min_tax_enabled=excluded.min_tax_enabled,
      updated_at=excluded.updated_at
    ''',(telegram_id,mode,rate,int(min_tax_enabled or 0),now))
    conn.commit(); conn.close()
    return get_tax_settings(telegram_id)

def calculate_tax(telegram_id, revenue, profit_before_tax):
    settings=get_tax_settings(telegram_id)
    mode=settings['tax_mode']
    rate=float(settings['tax_rate'] or 0)
    revenue=float(revenue or 0)
    profit_before_tax=float(profit_before_tax or 0)
    warning=None; notes=[]; tax=0.0
    if mode == 'none':
        warning='Налоговая система не настроена'
    elif mode in ('usn_income','npd'):
        tax=revenue*rate/100.0
    elif mode == 'usn_profit':
        tax=max(profit_before_tax,0)*rate/100.0
        if int(settings['min_tax_enabled'] or 0):
            minimum_tax=revenue*0.01
            if minimum_tax > tax:
                tax=minimum_tax
            notes.append('Минимальный налог 1% включён.')
    elif mode == 'custom':
        tax=max(profit_before_tax,0)*rate/100.0
    return {
        'settings': settings,
        'tax': round(tax,2),
        'warning': warning,
        'notes': notes,
        'configured': mode != 'none',
    }

def get_profit_stats_after_tax(days=None, telegram_id=None):
    st=get_profit_stats(days, telegram_id)
    tax_data=calculate_tax(telegram_id, st[0], st[10])
    profit_after_tax=round((st[10] or 0)-(tax_data['tax'] or 0),2)
    margin_after_tax=round((profit_after_tax/(st[2] or 0)*100) if (st[2] or 0) else 0,1)
    return {
        'base': st,
        'profit_before_tax': round(st[10] or 0,2),
        'tax': round(tax_data['tax'] or 0,2),
        'profit_after_tax': profit_after_tax,
        'margin_after_tax': margin_after_tax,
        'tax_warning': tax_data['warning'],
        'tax_notes': list(tax_data['notes']),
        'tax_settings': tax_data['settings'],
        'tax_configured': bool(tax_data['configured']),
    }

def format_tax_settings_label(telegram_id):
    s=get_tax_settings(telegram_id); mode=s['tax_mode']; rate=float(s['tax_rate'] or 0)
    if mode == 'usn_income': return f'УСН доходы {rate:g}%'
    if mode == 'usn_profit': return f'УСН доходы минус расходы {rate:g}%' + (' (мин. налог 1%)' if int(s['min_tax_enabled'] or 0) else '')
    if mode == 'npd': return f'НПД {rate:g}%'
    if mode == 'custom': return f'Пользовательский режим {rate:g}%'
    return 'Не настроен'

def get_replenishment_settings(telegram_id):
    init_db(); conn=_conn(); cur=conn.cursor()
    cur.execute('''
    SELECT sales_window_days,target_stock_days,lead_time_days,safety_stock_days,min_order_qty,updated_at
    FROM replenishment_settings
    WHERE telegram_id=?
    ''',(telegram_id,))
    row=cur.fetchone(); conn.close()
    settings={
        'telegram_id':telegram_id,
        'sales_window_days':30,
        'target_stock_days':45,
        'lead_time_days':14,
        'safety_stock_days':7,
        'min_order_qty':0,
        'updated_at':None,
    }
    if row:
        settings.update({
            'sales_window_days':int(row[0] or 30),
            'target_stock_days':int(row[1] or 45),
            'lead_time_days':int(row[2] or 14),
            'safety_stock_days':int(row[3] or 7),
            'min_order_qty':int(row[4] or 0),
            'updated_at':row[5],
        })
    return settings

def set_replenishment_settings(telegram_id, sales_window_days=None, target_stock_days=None, lead_time_days=None, safety_stock_days=None, min_order_qty=None):
    current=get_replenishment_settings(telegram_id)
    values={
        'sales_window_days': current['sales_window_days'] if sales_window_days is None else int(sales_window_days),
        'target_stock_days': current['target_stock_days'] if target_stock_days is None else int(target_stock_days),
        'lead_time_days': current['lead_time_days'] if lead_time_days is None else int(lead_time_days),
        'safety_stock_days': current['safety_stock_days'] if safety_stock_days is None else int(safety_stock_days),
        'min_order_qty': current['min_order_qty'] if min_order_qty is None else int(min_order_qty),
    }
    ranges={
        'sales_window_days':(7,90,'Окно продаж должно быть от 7 до 90 дней'),
        'target_stock_days':(7,180,'Целевой запас должен быть от 7 до 180 дней'),
        'lead_time_days':(0,90,'Срок поставки должен быть от 0 до 90 дней'),
        'safety_stock_days':(0,90,'Страховой запас должен быть от 0 до 90 дней'),
        'min_order_qty':(0,100000,'Минимальная партия должна быть от 0 до 100000'),
    }
    for key,(low,high,msg) in ranges.items():
        if values[key] < low or values[key] > high:
            raise ValueError(msg)
    now=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn=_conn(); cur=conn.cursor()
    cur.execute('''
    INSERT INTO replenishment_settings(
        telegram_id,sales_window_days,target_stock_days,lead_time_days,safety_stock_days,min_order_qty,updated_at
    ) VALUES(?,?,?,?,?,?,?)
    ON CONFLICT(telegram_id) DO UPDATE SET
        sales_window_days=excluded.sales_window_days,
        target_stock_days=excluded.target_stock_days,
        lead_time_days=excluded.lead_time_days,
        safety_stock_days=excluded.safety_stock_days,
        min_order_qty=excluded.min_order_qty,
        updated_at=excluded.updated_at
    ''',(
        telegram_id,
        values['sales_window_days'],
        values['target_stock_days'],
        values['lead_time_days'],
        values['safety_stock_days'],
        values['min_order_qty'],
        now
    ))
    conn.commit(); conn.close()
    return get_replenishment_settings(telegram_id)

def get_roi(days=None, telegram_id=None, article=None):
    if article:
        s=get_product_stats(article, days, telegram_id)
        base=(s[4] or 0)+(s[9] or 0)
        return round((s[11]/base*100),1) if base>0 else None
    st=get_profit_stats(days, telegram_id)
    base=(st[3] or 0)+(st[8] or 0)
    return round((st[10]/base*100),1) if base>0 else None

def get_product_stats(article, days=None, telegram_id=None):
    days=allowed_days(telegram_id, days) if telegram_id else days; conn=_conn(); cur=conn.cursor(); where,params=_where('s',telegram_id,days); where=(where+' AND ' if where else 'WHERE ')+'s.supplier_article=?'; params.append(article)
    cur.execute(f'''SELECT COUNT(*),COALESCE(SUM(s.price_with_disc),0),COALESCE(SUM(s.for_pay),0),COALESCE(SUM(COALESCE((SELECT p2.cost_price FROM products p2 WHERE p2.supplier_article=s.supplier_article AND p2.telegram_id IN (s.telegram_id,0) ORDER BY p2.telegram_id DESC LIMIT 1),0)),0),COALESCE(SUM(CASE WHEN s.is_return=1 THEN 1 ELSE 0 END),0) FROM sales s {where}''',params)
    cnt,sales,payout,cost,ret=cur.fetchone(); conn.close(); logi,adv,stor,other,exp=get_expenses_total(telegram_id,days,article); comm=sales-payout; gross=payout-cost; net=gross-exp; margin=net/payout*100 if payout else 0
    return (int(cnt or 0),round(sales,2),round(comm,2),round(payout,2),round(cost,2),logi,adv,stor,other,exp,round(gross,2),round(net,2),round(margin,1),int(ret or 0))

def get_advertising_stats(days=None, telegram_id=None, article=None):
    days=allowed_days(telegram_id, days) if telegram_id else days; conn=_conn(); cur=conn.cursor(); q='SELECT COALESCE(SUM(views),0),COALESCE(SUM(clicks),0),COALESCE(SUM(orders),0),COALESCE(SUM(sum_price),0),COALESCE(SUM(spend),0) FROM advertising WHERE 1=1'; params=[]
    if telegram_id is not None: q+=' AND telegram_id=?'; params.append(telegram_id)
    if days is not None:
        if _is_date_range(days): q+=' AND substr(advert_date,1,10) BETWEEN ? AND ?'; params.extend([days[0], days[1]])
        elif days==1: q+=" AND substr(advert_date,1,10)=date('now')"
        else: q+=' AND substr(advert_date,1,10)>=?'; params.append(_from(days))
    if article: q+=' AND supplier_article=?'; params.append(article)
    cur.execute(q,params); views,clicks,orders,sum_price,spend=cur.fetchone(); conn.close(); ctr=clicks/views*100 if views else 0; cpc=spend/clicks if clicks else 0; roas=sum_price/spend if spend else 0; drr=spend/sum_price*100 if sum_price else 0
    return (int(views or 0),int(clicks or 0),int(orders or 0),round(sum_price or 0,2),round(spend or 0,2),round(ctr,2),round(cpc,2),round(roas,2),round(drr,1))

def get_stocks(telegram_id=None):
    conn=_conn(); cur=conn.cursor(); cur.execute('''SELECT supplier_article,SUM(quantity),SUM(quantity_full),SUM(in_way_to_client),SUM(in_way_from_client),GROUP_CONCAT(DISTINCT warehouse_name) FROM stocks WHERE telegram_id=? AND stock_date=(SELECT MAX(stock_date) FROM stocks WHERE telegram_id=?) GROUP BY supplier_article ORDER BY SUM(quantity) ASC''',(telegram_id,telegram_id)); rows=cur.fetchall(); conn.close(); return rows

def get_daily_sales(telegram_id=None, days=30):
    days=allowed_days(telegram_id, days) if telegram_id else days; conn=_conn(); cur=conn.cursor(); where,params=_where('s',telegram_id,days); cur.execute(f'SELECT substr(sale_date,1,10),COALESCE(SUM(for_pay),0),COUNT(*) FROM sales s {where} GROUP BY 1 ORDER BY 1',params); rows=cur.fetchall(); conn.close(); return rows

def get_revenue_structure(telegram_id=None, group_by='supplier_article'):
    col={'supplier_article':'supplier_article','brand':'brand','category':'category','warehouse':'warehouse_name'}.get(group_by,'supplier_article'); conn=_conn(); cur=conn.cursor(); where,params=_where('s',telegram_id,None); cur.execute(f"SELECT COALESCE(s.{col},'-'),COALESCE(SUM(s.for_pay),0),COUNT(*) FROM sales s {where} GROUP BY COALESCE(s.{col},'-') ORDER BY 2 DESC",params); rows=cur.fetchall(); conn.close(); return rows

def get_abc_analysis(telegram_id=None):
    rows=get_revenue_structure(telegram_id,'supplier_article'); total=sum(x[1] for x in rows); out=[]; cum=0
    if not total: return []
    for name,rev,_ in rows: share=rev/total*100; cum+=share; out.append((name,round(share,1),'A' if cum<=80 else 'B' if cum<=95 else 'C'))
    return out

def get_margin_by_sku(days=None, telegram_id=None, limit=50):
    return [(r[0], r[9], r[10]) for r in get_top_margin_products(days, limit, telegram_id)]

def get_growth(telegram_id=None):
    rows=get_daily_sales(telegram_id,60)
    if len(rows)<2 or not rows[-2][1]: return None
    return round((rows[-1][1]-rows[-2][1])/rows[-2][1]*100,1)
def get_revenue_forecast(telegram_id=None):
    rows=get_daily_sales(telegram_id,30); return round(sum(r[1] for r in rows)/len(rows)*30,2) if rows else 0

def _profit_rows(days=None, telegram_id=None, limit=10, order='DESC', order_by='net_profit'):
    days=allowed_days(telegram_id, days) if telegram_id else days; conn=_conn(); cur=conn.cursor(); where,params=_where('s',telegram_id,days); cost_sql=_catalog_cost_lookup_sql('s'); cur.execute(f'''SELECT s.supplier_article,COALESCE(SUM(s.for_pay),0),COALESCE(SUM({cost_sql}),0),COALESCE(SUM(CASE WHEN s.is_return=1 THEN 1 ELSE 0 END),0) FROM sales s {where} GROUP BY s.supplier_article HAVING SUM(s.for_pay)>0''',params); base=cur.fetchall(); conn.close(); res=[]
    for a,payout,cost,ret in base:
        logi,adv,stor,other,exp=get_expenses_total(telegram_id,days,a); gross=payout-cost; net=gross-exp; margin=net/payout*100 if payout else 0; res.append((a,round(payout,2),round(cost,2),round(gross,2),logi,adv,stor,other,exp,round(net,2),round(margin,1),int(ret or 0)))
    idx={'revenue':1,'margin':10,'net_profit':9}.get(order_by,9); res.sort(key=lambda r:r[idx], reverse=(order.upper()=='DESC')); return res[:limit]
def get_top_profit_skus(telegram_id, days, limit=10, order='DESC'):
    days=allowed_days(telegram_id, days) if telegram_id else days; conn=_conn(); cur=conn.cursor(); where,params=_where('s',telegram_id,days); cost_sql=_catalog_cost_lookup_sql('s')
    cur.execute(f'''SELECT COALESCE(s.supplier_article,'-'),COALESCE(SUM(s.price_with_disc),0),COALESCE(SUM(s.for_pay),0),COALESCE(SUM({cost_sql}),0),COALESCE(SUM(CASE WHEN s.is_return=1 THEN 1 ELSE 0 END),0),COALESCE(SUM(CASE WHEN COALESCE(s.is_return,0)=0 THEN 1 ELSE 0 END),0) FROM sales s {where} GROUP BY COALESCE(s.supplier_article,'-') HAVING COALESCE(SUM(s.price_with_disc),0)<>0 OR COALESCE(SUM(s.for_pay),0)<>0''',params); base=cur.fetchall(); conn.close(); rows=[]
    total_logi,total_adv,total_stor,total_other,_=get_expenses_total(telegram_id,days)
    total_revenue=sum(float(row[1] or 0) for row in base)
    total_payout=sum(float(row[2] or 0) for row in base)
    direct={}
    for article,revenue,payout,cost,ret,sales_count in base:
        logi,adv,stor,other,exp=get_expenses_total(telegram_id,days,article)
        direct[article or '-']={'logistics':float(logi or 0),'advertising':float(adv or 0),'storage':float(stor or 0),'other':float(other or 0)}
    direct_sums={
        'logistics':sum(v['logistics'] for v in direct.values()),
        'advertising':sum(v['advertising'] for v in direct.values()),
        'storage':sum(v['storage'] for v in direct.values()),
        'other':sum(v['other'] for v in direct.values()),
    }
    remainders={
        'logistics':max(0.0,float(total_logi or 0)-direct_sums['logistics']),
        'advertising':max(0.0,float(total_adv or 0)-direct_sums['advertising']),
        'storage':max(0.0,float(total_stor or 0)-direct_sums['storage']),
        'other':max(0.0,float(total_other or 0)-direct_sums['other']),
    }
    for article,revenue,payout,cost,ret,sales_count in base:
        article=article or '-'; revenue=float(revenue or 0); payout=float(payout or 0); cost=float(cost or 0)
        share=(payout/total_payout) if total_payout>0 else ((revenue/total_revenue) if total_revenue>0 else 0.0)
        direct_row=direct.get(article,{})
        logistics=float(direct_row.get('logistics') or 0)
        advertising=float(direct_row.get('advertising') or 0)
        storage=float(direct_row.get('storage') or 0)
        other=float(direct_row.get('other') or 0)
        if logistics <= 0:
            logistics += remainders['logistics'] * share
        if advertising <= 0:
            advertising += remainders['advertising'] * share
        if storage <= 0:
            storage += remainders['storage'] * share
        if other <= 0:
            other += remainders['other'] * share
        expenses_total=cost+logistics+advertising+storage+other
        profit_before_tax=payout-expenses_total
        margin=profit_before_tax/payout*100 if payout else 0
        rows.append({'article':article,'sales_count':int(sales_count or 0),'revenue':round(revenue,2),'payout':round(payout,2),'cost':round(cost,2),'logistics':round(logistics,2),'advertising':round(advertising,2),'storage':round(storage,2),'other':round(other,2),'expenses_total':round(expenses_total,2),'profit_before_tax':round(profit_before_tax,2),'margin':round(float(margin or 0),1),'returns':int(ret or 0)})
    rows.sort(key=lambda r:r['profit_before_tax'], reverse=(order.upper()=='DESC')); return rows[:limit]
def get_top_profit_products(days=None, limit=10, telegram_id=None, order_by='net_profit'): return _profit_rows(days,telegram_id,limit,'DESC',order_by)
def get_worst_profit_products(days=None, top_n=10, telegram_id=None): return _profit_rows(days,telegram_id,top_n,'ASC','net_profit')
def get_top_margin_products(days=None, top_n=10, telegram_id=None): return _profit_rows(days,telegram_id,top_n,'DESC','margin')
def get_top_product(telegram_id=None):
    r=get_top_profit_products(telegram_id=telegram_id,order_by='revenue',limit=1); return (r[0][0],r[0][1]) if r else None
def get_worst_product(telegram_id=None):
    r=get_worst_profit_products(telegram_id=telegram_id,top_n=1); return (r[0][0],r[0][9]) if r else None

def set_plan(telegram_id, period='month', revenue_plan=0, profit_plan=0, orders_plan=0):
    conn=_conn(); cur=conn.cursor(); cur.execute('INSERT INTO plans(telegram_id,plan_period,revenue_plan,profit_plan,orders_plan,created_at) VALUES(?,?,?,?,?,?)',(telegram_id,period,float(revenue_plan or 0),float(profit_plan or 0),int(orders_plan or 0),datetime.now().strftime('%Y-%m-%d %H:%M:%S'))); conn.commit(); conn.close()
def get_last_plan(telegram_id, period='month'):
    conn=_conn(); cur=conn.cursor(); cur.execute('SELECT revenue_plan,profit_plan,orders_plan FROM plans WHERE telegram_id=? AND plan_period=? ORDER BY id DESC LIMIT 1',(telegram_id,period)); row=cur.fetchone(); conn.close(); return row
def get_plan_fact(telegram_id, period='month'):
    p,days=normalize_period(period); plan=get_last_plan(telegram_id,p) or (0,0,0); st=get_profit_stats(days,telegram_id); od=get_orders_stats(days,telegram_id); return {'period':p,'revenue_plan':float(plan[0] or 0),'revenue_fact':st[2],'profit_plan':float(plan[1] or 0),'profit_fact':st[10],'orders_plan':int(plan[2] or 0),'orders_fact':od[0]}
def compare_periods(telegram_id, period='month'):
    p,days=normalize_period(period); days=days or 30; cur=get_profit_stats(days,telegram_id); end=datetime.now()-timedelta(days=days); start=datetime.now()-timedelta(days=days*2-1); conn=_conn(); c=conn.cursor(); c.execute('SELECT COALESCE(SUM(for_pay),0),COUNT(*) FROM sales WHERE telegram_id=? AND substr(sale_date,1,10) BETWEEN ? AND ?',(telegram_id,start.strftime('%Y-%m-%d'),end.strftime('%Y-%m-%d'))); prev,pc=c.fetchone(); conn.close(); return {'period':p,'current_payout':cur[2],'current_profit':cur[10],'current_count':get_period_stats(days,telegram_id)[0],'prev_payout':prev or 0,'prev_count':pc or 0}
def get_cash_gap(telegram_id, days=14, sales_window=30):
    sales_window=max(1,int(sales_window or 30)); stocks=get_stocks(telegram_id); conn=_conn(); cur=conn.cursor()
    cur.execute('''
    SELECT supplier_article, COUNT(*)
    FROM sales
    WHERE telegram_id=? AND substr(sale_date,1,10)>=?
    GROUP BY supplier_article
    ''',(telegram_id,_from(sales_window)))
    daily={str(a or ''):float(c or 0)/sales_window for a,c in cur.fetchall()}; conn.close(); out=[]
    for a,qty,*_ in stocks:
        avg=daily.get(str(a or ''),0); 
        if avg<=0: continue
        left=(qty or 0)/avg; 
        if left<=days:
            cost=(get_catalog_cost_price(telegram_id, supplier_article=a) or 0); need=max(0,int(avg*days-(qty or 0))); out.append((a,qty or 0,round(left,1),need,round(need*cost,2)))
    return out, round(sum(x[4] for x in out),2)

def get_sku_sales_velocity(telegram_id, days=30):
    days=max(1,int(days or 30))
    conn=_conn(); cur=conn.cursor()
    cur.execute('''
    SELECT supplier_article, COUNT(*), COALESCE(SUM(for_pay),0)
    FROM sales
    WHERE telegram_id=? AND substr(sale_date,1,10)>=? AND COALESCE(is_return,0)=0
    GROUP BY supplier_article
    ''',(telegram_id,_from(days)))
    rows=cur.fetchall(); conn.close(); out={}
    for article,count,revenue in rows:
        article=str(article or '').strip()
        if not article:
            continue
        sales_count=int(count or 0)
        out[article]={
            'article':article,
            'sales_count':sales_count,
            'revenue':round(float(revenue or 0),2),
            'avg_sales_per_day':round(sales_count/days,4),
            'window_days':days,
        }
    return out

def _risk_level(current_stock, days_left):
    if current_stock <= 0:
        return 'no_stock'
    if days_left is None:
        return 'no_sales'
    if days_left <= 7:
        return 'critical'
    if days_left <= 14:
        return 'high'
    return 'ok'

def get_stock_forecast(telegram_id, days=14, sales_window=30):
    sales_window=max(1,int(sales_window or 30))
    horizon=max(1,int(days or 14))
    settings=get_replenishment_settings(telegram_id)
    velocity=get_sku_sales_velocity(telegram_id, sales_window)
    conn=_conn(); cur=conn.cursor()
    cur.execute('SELECT MAX(stock_date) FROM stocks WHERE telegram_id=?',(telegram_id,))
    snapshot_date=cur.fetchone()[0]
    if not snapshot_date:
        conn.close()
        return []
    cur.execute('''
    SELECT supplier_article,
           COALESCE(SUM(quantity),0),
           COALESCE(SUM(quantity_full),0),
           COALESCE(SUM(in_way_to_client),0),
           COALESCE(SUM(in_way_from_client),0)
    FROM stocks
    WHERE telegram_id=? AND stock_date=?
    GROUP BY supplier_article
    ORDER BY supplier_article
    ''',(telegram_id,snapshot_date))
    stock_rows=cur.fetchall()
    costs=get_product_catalog_cost_map(telegram_id)
    conn.close()
    rows=[]; today=datetime.now().date()
    demand_horizon=max(horizon, settings['target_stock_days'] + settings['lead_time_days'] + settings['safety_stock_days'])
    for article,qty,qty_full,to_client,from_client in stock_rows:
        article=str(article or '').strip()
        if not article:
            continue
        current_stock=int(qty or 0)
        quantity_full=int(qty_full or 0)
        in_way_to_client=int(to_client or 0)
        in_way_from_client=int(from_client or 0)
        v=velocity.get(article,{})
        avg_sales_per_day=float(v.get('avg_sales_per_day') or 0)
        days_left=round(current_stock/avg_sales_per_day,1) if avg_sales_per_day > 0 else None
        oos_date=(today + timedelta(days=max(days_left,0))).strftime('%Y-%m-%d') if days_left is not None else None
        available_stock=current_stock + in_way_from_client
        target_units=avg_sales_per_day * demand_horizon
        raw_need=max(0, ceil(target_units - available_stock))
        min_order_qty=int(settings['min_order_qty'] or 0)
        need=max(raw_need, min_order_qty) if raw_need > 0 and min_order_qty > 0 else raw_need
        cost_price=float(costs.get(article,0) or 0)
        cost_missing=cost_price <= 0
        budget=round(need * cost_price,2)
        rows.append({
            'article':article,
            'supplier_article':article,
            'qty':current_stock,
            'current_stock':current_stock,
            'available_stock':available_stock,
            'quantity_full':quantity_full,
            'in_way_to_client':in_way_to_client,
            'in_way_from_client':in_way_from_client,
            'avg_sales_per_day':round(avg_sales_per_day,2),
            'days_left':days_left,
            'oos_date':oos_date,
            'risk_level':_risk_level(current_stock, days_left),
            'need':need,
            'budget':budget,
            'cost_price':round(cost_price,2),
            'cost_missing':cost_missing,
            'sales_window_days':sales_window,
            'snapshot_date':snapshot_date,
            'target_stock_days':settings['target_stock_days'],
            'lead_time_days':settings['lead_time_days'],
            'safety_stock_days':settings['safety_stock_days'],
            'demand_horizon_days':demand_horizon,
            'sales_count_window':int(v.get('sales_count') or 0),
        })
    rows.sort(key=lambda r: (
        {'no_stock':0,'critical':1,'high':2,'ok':3,'no_sales':4}.get(r['risk_level'],9),
        999999 if r['days_left'] is None else r['days_left'],
        r['article']
    ))
    return rows

def get_replenishment_plan(telegram_id):
    settings=get_replenishment_settings(telegram_id)
    rows=get_stock_forecast(
        telegram_id,
        settings['target_stock_days'] + settings['lead_time_days'] + settings['safety_stock_days'],
        settings['sales_window_days']
    )
    items=[]; total_budget=0.0; total_units=0
    for row in rows:
        if (row['avg_sales_per_day'] or 0) <= 0 or (row['need'] or 0) <= 0:
            continue
        item=dict(row)
        item['coverage_days_target']=settings['target_stock_days']
        items.append(item)
        total_budget += float(item['budget'] or 0)
        total_units += int(item['need'] or 0)
    return {
        'settings':settings,
        'items':items,
        'total_budget':round(total_budget,2),
        'total_units':total_units,
        'generated_at':datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
def get_price_recommendations(telegram_id, days=30):
    out=[]
    for a,payout,cost,gross,logi,adv,stor,other,exp,net,margin,ret in get_top_profit_products(days,100,telegram_id):
        action='держать цену'
        if margin<10: action='поднять цену или снизить рекламу/себестоимость'
        elif margin>35 and ret==0: action='тестово поднять цену на 3–7%'
        elif adv>gross and adv>0: action='остановить/пересобрать рекламу'
        out.append((a,margin,net,adv,ret,action))
    return out
