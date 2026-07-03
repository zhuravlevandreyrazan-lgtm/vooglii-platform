import sqlite3
import logging
from datetime import datetime, timedelta, time as dt_time
from time import time

from config import DB_NAME
from db_manager import init_db
from load_sales import sync_block_for_user, update_sync_status
from report import calculate_tax, format_tax_settings_label, get_advertising_stats, get_cost_fill_stats, get_daily_sales, get_profit_stats, get_profit_stats_after_tax, get_replenishment_plan, get_roi, get_stock_forecast, get_top_product, get_worst_profit_products
from update_log import save_update
from user_manager import get_active_user_tokens


logger = logging.getLogger(__name__)


SYNC_INTERVALS = {
    'sales': 1800,
    'orders': 1800,
    'stocks': 7200,
    'advertising': 7200,
    'finance': 21600,
}


def _get_target_users(telegram_id=None):
    return get_active_user_tokens(telegram_id)


def _job_telegram_id(context):
    if not getattr(context, 'job', None):
        return None
    data = getattr(context.job, 'data', None) or {}
    return data.get('telegram_id')


def _parse_dt(value):
    if not value:
        return None
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(str(value), fmt)
        except Exception:
            pass
    return None


def _sync_lock_row(telegram_id, sync_block):
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT started_at FROM sync_locks WHERE telegram_id=? AND sync_block=?', (telegram_id, sync_block))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def acquire_sync_lock(telegram_id, sync_block, max_age_minutes=30):
    init_db()
    started_at = _sync_lock_row(telegram_id, sync_block)
    now = datetime.now()
    if started_at:
        dt = _parse_dt(started_at)
        if dt and now - dt < timedelta(minutes=max_age_minutes):
            return False
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('DELETE FROM sync_locks WHERE telegram_id=? AND sync_block=?', (telegram_id, sync_block))
    cur.execute(
        'INSERT INTO sync_locks(telegram_id,sync_block,started_at) VALUES(?,?,?)',
        (telegram_id, sync_block, now.strftime('%Y-%m-%d %H:%M:%S'))
    )
    conn.commit()
    conn.close()
    return True


def release_sync_lock(telegram_id, sync_block):
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('DELETE FROM sync_locks WHERE telegram_id=? AND sync_block=?', (telegram_id, sync_block))
    conn.commit()
    conn.close()


def _sync_many(block, telegram_id=None):
    for user_id, token in _get_target_users(telegram_id):
        lock_acquired = False
        try:
            lock_acquired = acquire_sync_lock(user_id, block)
            if not lock_acquired:
                logger.warning('SYNC_SKIP_LOCK block=%s user_id=%s', block, user_id)
                continue
            sync_block_for_user(user_id, token, block, 30, save_update_row=True)
        except Exception as e:
            message = f'SYNC_ERROR:{block}:{type(e).__name__}'
            logger.exception(message)
            save_update(message, 0, user_id, 0, 0, 0, 0)
            update_sync_status(user_id, block, f'EXCEPTION:{type(e).__name__}')
        finally:
            if lock_acquired:
                release_sync_lock(user_id, block)


async def sync_sales_job(context):
    _sync_many('sales', _job_telegram_id(context))


async def sync_orders_job(context):
    _sync_many('orders', _job_telegram_id(context))


async def sync_stocks_job(context):
    _sync_many('stocks', _job_telegram_id(context))


async def sync_finance_job(context):
    _sync_many('finance', _job_telegram_id(context))


async def sync_ads_job(context):
    _sync_many('advertising', _job_telegram_id(context))


def schedule_background_jobs(job_queue):
    if not job_queue:
        return
    job_queue.run_repeating(sync_sales_job, interval=SYNC_INTERVALS['sales'], first=30, name='wb_sync_sales')
    job_queue.run_repeating(sync_orders_job, interval=SYNC_INTERVALS['orders'], first=60, name='wb_sync_orders')
    job_queue.run_repeating(sync_stocks_job, interval=SYNC_INTERVALS['stocks'], first=90, name='wb_sync_stocks')
    job_queue.run_repeating(sync_ads_job, interval=SYNC_INTERVALS['advertising'], first=120, name='wb_sync_advertising')
    job_queue.run_repeating(sync_finance_job, interval=SYNC_INTERVALS['finance'], first=150, name='wb_sync_finance')
    job_queue.run_repeating(alerts_job, interval=3600, first=300, name='wb_alerts')
    job_queue.run_daily(daily_ceo_job, time=dt_time(hour=9, minute=0), name='wb_daily_ceo')
    job_queue.run_daily(weekly_ceo_job, time=dt_time(hour=9, minute=5), name='wb_weekly_ceo')


def schedule_initial_sync(job_queue, telegram_id):
    if not job_queue:
        return
    suffix = f'{telegram_id}_{int(time())}'
    data = {'telegram_id': telegram_id}
    job_queue.run_once(sync_sales_job, when=5, data=data, name=f'wb_init_sales_{suffix}')
    job_queue.run_once(sync_orders_job, when=10, data=data, name=f'wb_init_orders_{suffix}')
    job_queue.run_once(sync_stocks_job, when=15, data=data, name=f'wb_init_stocks_{suffix}')
    job_queue.run_once(sync_ads_job, when=20, data=data, name=f'wb_init_ads_{suffix}')
    job_queue.run_once(sync_finance_job, when=25, data=data, name=f'wb_init_finance_{suffix}')


def _get_notification_settings(telegram_id):
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
    SELECT daily_enabled,daily_hour,weekly_enabled,low_stock_threshold,negative_profit_alert,drr_alert_threshold,sales_drop_threshold
    FROM notifications
    WHERE telegram_id=?
    ''', (telegram_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return {
            'daily_enabled': 0,
            'daily_hour': 9,
            'weekly_enabled': 1,
            'low_stock_threshold': 5,
            'negative_profit_alert': 1,
            'drr_alert_threshold': 30.0,
            'sales_drop_threshold': 40.0,
        }
    return {
        'daily_enabled': int(row[0] or 0),
        'daily_hour': int(row[1] or 9),
        'weekly_enabled': int(row[2] or 1),
        'low_stock_threshold': int(row[3] or 5),
        'negative_profit_alert': int(row[4] or 1),
        'drr_alert_threshold': float(row[5] or 30),
        'sales_drop_threshold': float(row[6] or 40),
    }


def _mark_alert_key(telegram_id, key, details):
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO audit_log(telegram_id,event_time,action,details) VALUES(?,?,?,?)',
        (telegram_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), key, details)
    )
    conn.commit()
    conn.close()


def _sales_drop_percent(telegram_id):
    rows = get_daily_sales(telegram_id, 14)
    if len(rows) < 4:
        return None
    values = [float(r[1] or 0) for r in rows]
    recent = values[-3:]
    prev = values[-10:-3] if len(values) >= 10 else values[:-3]
    if not prev:
        return None
    recent_avg = sum(recent) / len(recent)
    prev_avg = sum(prev) / len(prev)
    if prev_avg <= 0:
        return None
    return round((prev_avg - recent_avg) / prev_avg * 100, 1)


def _legacy_build_ceo_summary_v1(telegram_id, label='today'):
    days = 1 if label == 'today' else 7
    st = get_profit_stats(days, telegram_id)
    ad = get_advertising_stats(days, telegram_id)
    top = get_top_product(telegram_id)
    roi_base = (st[3] or 0) + (st[8] or 0)
    roi = round((st[10] / roi_base * 100) if roi_base else 0, 1)
    return (
        f"👑 CEO-отчёт ({'сегодня' if days == 1 else 'неделя'})\n\n"
        f"К выплате: {st[2]:,.2f} ₽\n"
        f"Чистая прибыль: {st[10]:,.2f} ₽\n"
        f"ROI: {roi:.1f}%\n"
        f"Маржа: {st[11]:.1f}%\n"
        f"Реклама: {ad[4]:,.2f} ₽ | ДРР {ad[8]:.1f}%\n"
        f"Лидер: {top[0] if top else '-'}"
    ).replace(',', ' ')


def _legacy_build_alerts_for_user_v1(telegram_id):
    settings = _get_notification_settings(telegram_id)
    alerts = []

    low_rows = [
        r for r in get_stock_forecast(telegram_id, 7, 30)
        if (r['qty'] or 0) <= settings['low_stock_threshold'] or (r['days_left'] or 999) <= 3
    ]
    low_rows = [r for r in low_rows if not _alert_key_sent(telegram_id, f"low_stock:{telegram_id}:{r['article']}")]
    if low_rows:
        sample = '\n'.join(f"{r['article']}: остаток {r['qty']}, дней {r['days_left']}" for r in low_rows[:5])
        alerts.append((
            [f"low_stock:{telegram_id}:{r['article']}" for r in low_rows],
            "📦 Заканчиваются товары\n\n" + sample
        ))

    forecast_plan = get_replenishment_plan(telegram_id)
    forecast_rows = [
        r for r in forecast_plan['items']
        if r.get('risk_level') in ('no_stock', 'critical', 'high')
        and (r.get('need') or 0) > 0
        and (r.get('avg_sales_per_day') or 0) > 0
        and not _alert_key_sent(telegram_id, f"low_stock_forecast:{telegram_id}:{r['article']}")
    ]
    for row in forecast_rows[:5]:
        alerts.append((
            [f"low_stock_forecast:{telegram_id}:{row['article']}"],
            (
                "🚨 Риск окончания товара\n\n"
                f"Артикул:\n{row['article']}\n\n"
                f"Остаток:\n{row['current_stock']}\n\n"
                f"Хватит на:\n{row['days_left'] if row['days_left'] is not None else '-'}\n\n"
                f"Рекомендуемый заказ:\n{row['need']}\n\n"
                f"Бюджет закупки:\n{row['budget']:,.2f} ₽"
            ).replace(',', ' ')
        ))

    today_drr, prev_drr = _recent_drr_change(telegram_id)
    if (
        today_drr is not None
        and prev_drr is not None
        and today_drr >= settings['drr_alert_threshold']
        and today_drr > prev_drr + 10
        and not _alert_key_sent(telegram_id, f'drr_growth:{telegram_id}')
    ):
        alerts.append((
            [f'drr_growth:{telegram_id}'],
            f"📣 Резко вырос ДРР\n\nСейчас: {today_drr:.1f}%\nСредний ДРР за 7 дней: {prev_drr:.1f}%"
        ))

    sales_drop = _sales_drop_percent(telegram_id)
    if (
        sales_drop is not None
        and sales_drop >= settings['sales_drop_threshold']
        and not _alert_key_sent(telegram_id, f'sales_drop:{telegram_id}')
    ):
        alerts.append((
            [f'sales_drop:{telegram_id}'],
            f"📉 Упали продажи\n\nПадение среднего дневного payout: {sales_drop:.1f}%"
        ))

    if settings['negative_profit_alert']:
        bad = [r for r in get_worst_profit_products(7, 5, telegram_id) if (r[10] or 0) < 0]
        bad = [r for r in bad if not _alert_key_sent(telegram_id, f"negative_margin:{telegram_id}:{r[0]}")]
        if bad:
            sample = '\n'.join(f"{r[0]}: маржа {r[10]:.1f}% | прибыль {r[9]:,.2f} ₽".replace(',', ' ') for r in bad[:5])
            alerts.append((
                [f"negative_margin:{telegram_id}:{r[0]}" for r in bad],
                "⚠ Отрицательная маржа\n\n" + sample
            ))

    return alerts


async def _legacy_alerts_job_v1(context):
    for telegram_id in _get_notified_users():
        try:
            for keys, text in _build_alerts_for_user(telegram_id):
                await context.bot.send_message(telegram_id, text)
                for key in keys:
                    _mark_alert_key(telegram_id, key, text[:500])
        except Exception as e:
            print('ALERTS_ERROR', telegram_id, e)


def _legacy_build_ceo_summary_v2(telegram_id, label='today'):
    days = 1 if label == 'today' else 7
    st = get_profit_stats(days, telegram_id)
    after_tax = get_profit_stats_after_tax(days, telegram_id)
    ad = get_advertising_stats(days, telegram_id)
    top = get_top_product(telegram_id)
    roi = get_roi(days, telegram_id)
    cost_stats = get_cost_fill_stats(days, telegram_id)
    replenishment = get_replenishment_plan(telegram_id)
    critical_rows = [row for row in replenishment['items'] if row.get('risk_level') in ('no_stock', 'critical', 'high')]
    urgent_row = critical_rows[0] if critical_rows else (replenishment['items'][0] if replenishment['items'] else None)
    roi_text = f"{roi:.1f}%" if roi is not None else "не рассчитан"
    footer = []
    if cost_stats['all_missing']:
        footer.append("⚠ Себестоимость не заполнена.")
    elif cost_stats['partial_missing']:
        footer.append("⚠ Себестоимость заполнена не у всех товаров.")
    if after_tax['tax_warning']:
        footer.append("⚠ Налоговая система не настроена. Прибыль показана до налога.")
    footer.extend(after_tax['tax_notes'])
    if replenishment['items']:
        footer.append(f"📦 Закупки\nКритических SKU: {len(critical_rows)}\nПлан закупки: {replenishment['total_budget']:,.2f} ₽".replace(',', ' '))
        if urgent_row:
            footer.append(f"Самый срочный:\n{urgent_row['article']}\nДней до окончания: {urgent_row['days_left'] if urgent_row['days_left'] is not None else '-'}")
        if any(row.get('cost_missing') for row in replenishment['items']):
            footer.append("⚠ Себестоимость не заполнена. Бюджет закупки может быть занижен.")
    else:
        footer.append("📦 Закупки\nНе хватает данных для прогноза.")
    footer.append(f"Налоговый режим: {format_tax_settings_label(telegram_id)}")
    footer.append("Расчёт налога предварительный. Для официальной отчётности сверяйтесь с бухгалтером.")
    tail = ('\n' + '\n'.join(footer)) if footer else ''
    return (
        f"📒 CEO-отчёт ({'сегодня' if days == 1 else 'неделя'})\n\n"
        f"К выплате: {st[2]:,.2f} ₽\n"
        f"Прибыль до налога: {after_tax['profit_before_tax']:,.2f} ₽\n"
        f"Налог: {after_tax['tax']:,.2f} ₽\n"
        f"Чистая прибыль после налога: {after_tax['profit_after_tax']:,.2f} ₽\n"
        f"ROI: {roi_text}\n"
        f"Маржа: {st[11]:.1f}%\n"
        f"Маржа после налога: {after_tax['margin_after_tax']:.1f}%\n"
        f"Логистика: {st[4]:,.2f} ₽\n"
        f"Хранение: {st[6]:,.2f} ₽\n"
        f"Реклама: {ad[4]:,.2f} ₽ | ДРР {ad[8]:.1f}%\n"
        f"Прочие расходы: {st[7]:,.2f} ₽\n"
        f"Расходы всего: {st[8]:,.2f} ₽\n"
        f"Лидер: {top[0] if top else '-'}"
        f"{tail}"
    ).replace(',', ' ')


def _legacy_build_alerts_for_user_v2(telegram_id):
    settings = _get_notification_settings(telegram_id)
    alerts = []

    low_rows = [
        r for r in get_stock_forecast(telegram_id, 7, 30)
        if (r['qty'] or 0) <= settings['low_stock_threshold'] or (r['days_left'] or 999) <= 3
    ]
    low_rows = [r for r in low_rows if not _alert_key_sent(telegram_id, f"low_stock:{telegram_id}:{r['article']}")]
    if low_rows:
        sample = '\n'.join(f"{r['article']}: остаток {r['qty']}, дней {r['days_left']}" for r in low_rows[:5])
        alerts.append((
            [f"low_stock:{telegram_id}:{r['article']}" for r in low_rows],
            "📦 Заканчиваются товары\n\n" + sample
        ))

    forecast_plan = get_replenishment_plan(telegram_id)
    urgent_rows = [
        r for r in forecast_plan['items']
        if (r['risk_level'] == 'critical' or ((r['days_left'] or 999) <= max(3, forecast_plan['settings']['lead_time_days'])))
    ]
    urgent_rows = [r for r in urgent_rows if not _alert_key_sent(telegram_id, f"low_stock_forecast:{telegram_id}:{r['article']}")]
    if urgent_rows:
        sample = '\n'.join(
            f"{r['article']}: хватит на {r['days_left'] if r['days_left'] is not None else '-'} дн., заказать {r['need']} шт."
            for r in urgent_rows[:5]
        )
        alerts.append((
            [f"low_stock_forecast:{telegram_id}:{r['article']}" for r in urgent_rows],
            "⚠ Риск дефицита по прогнозу\n\n" + sample
        ))

    today_drr, prev_drr = _recent_drr_change(telegram_id)
    if (
        today_drr is not None
        and prev_drr is not None
        and today_drr >= settings['drr_alert_threshold']
        and today_drr > prev_drr + 10
        and not _alert_key_sent(telegram_id, f'drr_growth:{telegram_id}')
    ):
        alerts.append((
            [f'drr_growth:{telegram_id}'],
            f"📣 Резко вырос ДРР\n\nСейчас: {today_drr:.1f}%\nСредний ДРР за 7 дней: {prev_drr:.1f}%"
        ))

    sales_drop = _sales_drop_percent(telegram_id)
    if (
        sales_drop is not None
        and sales_drop >= settings['sales_drop_threshold']
        and not _alert_key_sent(telegram_id, f'sales_drop:{telegram_id}')
    ):
        alerts.append((
            [f'sales_drop:{telegram_id}'],
            f"📉 Упали продажи\n\nПадение среднего дневного payout: {sales_drop:.1f}%"
        ))

    if settings['negative_profit_alert']:
        bad = [r for r in get_worst_profit_products(7, 5, telegram_id) if (r[10] or 0) < 0]
        bad = [r for r in bad if not _alert_key_sent(telegram_id, f"negative_margin:{telegram_id}:{r[0]}")]
        if bad:
            sample = '\n'.join(f"{r[0]}: маржа {r[10]:.1f}% | прибыль {r[9]:,.2f} ₽".replace(',', ' ') for r in bad[:5])
            alerts.append((
                [f"negative_margin:{telegram_id}:{r[0]}" for r in bad],
                "⚠ Отрицательная маржа\n\n" + sample
            ))

    return alerts


async def _legacy_alerts_job_v2(context):
    for telegram_id in _get_notified_users():
        try:
            for keys, text in _build_alerts_for_user(telegram_id):
                await context.bot.send_message(telegram_id, text)
                for key in keys:
                    _mark_alert_key(telegram_id, key, text[:500])
        except Exception as e:
            print('ALERTS_ERROR', telegram_id, e)


def _legacy_build_ceo_summary_v3(telegram_id, label='today'):
    days = 1 if label == 'today' else 7
    st = get_profit_stats(days, telegram_id)
    after_tax = get_profit_stats_after_tax(days, telegram_id)
    ad = get_advertising_stats(days, telegram_id)
    top = get_top_product(telegram_id)
    roi = get_roi(days, telegram_id)
    cost_stats = get_cost_fill_stats(days, telegram_id)
    replenishment = get_replenishment_plan(telegram_id)
    roi_text = f"{roi:.1f}%" if roi is not None else "не рассчитан"
    footer = []
    if cost_stats['all_missing']:
        footer.append("⚠ Себестоимость не заполнена.")
    elif cost_stats['partial_missing']:
        footer.append("⚠ Себестоимость заполнена не у всех товаров.")
    if after_tax['tax_warning']:
        footer.append("⚠ Налоговая система не настроена. Прибыль показана до налога.")
    footer.extend(after_tax['tax_notes'])
    if replenishment['items']:
        top_need = ', '.join(f"{x['article']} ({x['need']} шт.)" for x in replenishment['items'][:3])
        footer.append(f"Закупка: {len(replenishment['items'])} SKU на {replenishment['total_budget']:,.2f} ₽".replace(',', ' '))
        footer.append(f"Топ к заказу: {top_need}")
    footer.append(f"Налоговый режим: {format_tax_settings_label(telegram_id)}")
    footer.append("Расчёт налога предварительный. Для официальной отчётности сверяйтесь с бухгалтером.")
    tail = ('\n' + '\n'.join(footer)) if footer else ''
    return (
        f"📒 CEO-отчёт ({'сегодня' if days == 1 else 'неделя'})\n\n"
        f"К выплате: {st[2]:,.2f} ₽\n"
        f"Прибыль до налога: {after_tax['profit_before_tax']:,.2f} ₽\n"
        f"Налог: {after_tax['tax']:,.2f} ₽\n"
        f"Чистая прибыль после налога: {after_tax['profit_after_tax']:,.2f} ₽\n"
        f"ROI: {roi_text}\n"
        f"Маржа: {st[11]:.1f}%\n"
        f"Маржа после налога: {after_tax['margin_after_tax']:.1f}%\n"
        f"Логистика: {st[4]:,.2f} ₽\n"
        f"Хранение: {st[6]:,.2f} ₽\n"
        f"Реклама: {ad[4]:,.2f} ₽ | ДРР {ad[8]:.1f}%\n"
        f"Прочие расходы: {st[7]:,.2f} ₽\n"
        f"Расходы всего: {st[8]:,.2f} ₽\n"
        f"Лидер: {top[0] if top else '-'}"
        f"{tail}"
    ).replace(',', ' ')


async def daily_ceo_job(context):
    for telegram_id in _get_notified_users():
        settings = _get_notification_settings(telegram_id)
        if not settings['daily_enabled']:
            continue
        try:
            await context.bot.send_message(telegram_id, _build_ceo_summary(telegram_id, 'today'))
        except Exception as e:
            print('DAILY_CEO_ERROR', telegram_id, e)


async def weekly_ceo_job(context):
    if datetime.now().weekday() != 0:
        return
    for telegram_id in _get_notified_users():
        settings = _get_notification_settings(telegram_id)
        if not settings['weekly_enabled']:
            continue
        try:
            await context.bot.send_message(telegram_id, _build_ceo_summary(telegram_id, 'week'))
        except Exception as e:
            print('WEEKLY_CEO_ERROR', telegram_id, e)


def _legacy_build_alerts_for_user_v3(telegram_id):
    settings = _get_notification_settings(telegram_id)
    alerts = []

    low_rows = [r for r in get_stock_forecast(telegram_id, 7) if (r['qty'] or 0) <= settings['low_stock_threshold'] or (r['days_left'] or 999) <= 3]
    if low_rows and not _alert_key_sent(telegram_id, 'ALERT_LOW_STOCK'):
        sample = '\n'.join(f"{r['article']}: остаток {r['qty']}, дней {r['days_left']}" for r in low_rows[:5])
        alerts.append(('ALERT_LOW_STOCK', "📦 Заканчиваются товары\n\n" + sample))

    today_drr, prev_drr = _recent_drr_change(telegram_id)
    if today_drr >= settings['drr_alert_threshold'] and today_drr > prev_drr + 10 and not _alert_key_sent(telegram_id, 'ALERT_DRR_SPIKE'):
        alerts.append(('ALERT_DRR_SPIKE', f"📢 Резко вырос ДРР\n\nСейчас: {today_drr:.1f}%\nБыло: {prev_drr:.1f}%"))

    sales_drop = _sales_drop_percent(telegram_id)
    if sales_drop is not None and sales_drop >= settings['sales_drop_threshold'] and not _alert_key_sent(telegram_id, 'ALERT_SALES_DROP'):
        alerts.append(('ALERT_SALES_DROP', f"📉 Упали продажи\n\nПадение среднего дневного payout: {sales_drop:.1f}%"))

    if settings['negative_profit_alert']:
        bad = [r for r in get_worst_profit_products(7, 5, telegram_id) if (r[10] or 0) < 0]
        if bad and not _alert_key_sent(telegram_id, 'ALERT_NEG_MARGIN'):
            sample = '\n'.join(f"{r[0]}: маржа {r[10]:.1f}% | прибыль {r[9]:,.2f} ₽".replace(',', ' ') for r in bad[:5])
            alerts.append(('ALERT_NEG_MARGIN', "⚠ Отрицательная маржа\n\n" + sample))

    return alerts


def _legacy_build_ceo_summary_v4(telegram_id, label='today'):
    days = 1 if label == 'today' else 7
    st = get_profit_stats(days, telegram_id)
    after_tax = get_profit_stats_after_tax(days, telegram_id)
    ad = get_advertising_stats(days, telegram_id)
    top = get_top_product(telegram_id)
    roi = get_roi(days, telegram_id)
    cost_stats = get_cost_fill_stats(days, telegram_id)
    roi_text = f"{roi:.1f}%" if roi is not None else "не рассчитан"
    footer = []
    if cost_stats['all_missing']:
        footer.append("⚠ Себестоимость не заполнена.")
    elif cost_stats['partial_missing']:
        footer.append("⚠ Себестоимость заполнена не у всех товаров.")
    if after_tax['tax_warning']:
        footer.append("⚠ Налоговая система не настроена. Прибыль показана до налога.")
    footer.extend(after_tax['tax_notes'])
    footer.append(f"Налоговый режим: {format_tax_settings_label(telegram_id)}")
    footer.append("Расчёт налога предварительный. Для официальной отчётности сверяйтесь с бухгалтером.")
    tail = ('\n' + '\n'.join(footer)) if footer else ''
    return (
        f"📒 CEO-отчёт ({'сегодня' if days == 1 else 'неделя'})\n\n"
        f"К выплате: {st[2]:,.2f} ₽\n"
        f"Прибыль до налога: {after_tax['profit_before_tax']:,.2f} ₽\n"
        f"Налог: {after_tax['tax']:,.2f} ₽\n"
        f"Чистая прибыль после налога: {after_tax['profit_after_tax']:,.2f} ₽\n"
        f"ROI: {roi_text}\n"
        f"Маржа: {st[11]:.1f}%\n"
        f"Маржа после налога: {after_tax['margin_after_tax']:.1f}%\n"
        f"Реклама: {ad[4]:,.2f} ₽ | ДРР {ad[8]:.1f}%\n"
        f"Лидер: {top[0] if top else '-'}"
        f"{tail}"
    ).replace(',', ' ')


async def _legacy_alerts_job_v3(context):
    for telegram_id in _get_notified_users():
        try:
            for key, text in _build_alerts_for_user(telegram_id):
                await context.bot.send_message(telegram_id, text)
                _mark_alert_key(telegram_id, key, text[:500])
        except Exception as e:
            print('ALERTS_ERROR', telegram_id, e)


def _get_notified_users():
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    cur.execute('''
    SELECT u.telegram_id
    FROM users u
    JOIN notifications n ON n.telegram_id=u.telegram_id
    WHERE u.is_active=1
      AND u.wb_token IS NOT NULL
      AND TRIM(u.wb_token)!=''
      AND UPPER(COALESCE(u.tariff,'FREE'))='PRO'
      AND (
          u.subscription_until IS NULL
          OR u.subscription_until=''
          OR u.subscription_until>=?
      )
    ORDER BY u.telegram_id
    ''', (today,))
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows


def _alert_key_sent(telegram_id, key, cooldown_hours=24):
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
    SELECT 1 FROM audit_log
    WHERE telegram_id=? AND action=? AND event_time>=?
    LIMIT 1
    ''', (telegram_id, key, (datetime.now() - timedelta(hours=cooldown_hours)).strftime('%Y-%m-%d %H:%M:%S')))
    row = cur.fetchone()
    conn.close()
    return bool(row)


def _recent_drr_change(telegram_id):
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    prev_from = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    prev_to = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    cur.execute('''
    SELECT COALESCE(SUM(spend),0), COALESCE(SUM(sum_price),0), COUNT(*)
    FROM advertising
    WHERE telegram_id=?
      AND substr(advert_date,1,10)=?
    ''', (telegram_id, today))
    today_spend, today_rev, today_rows = [float(x or 0) for x in cur.fetchone()]

    cur.execute('''
    SELECT AVG(daily_drr)
    FROM (
        SELECT SUM(spend) * 100.0 / SUM(sum_price) AS daily_drr
        FROM advertising
        WHERE telegram_id=?
          AND substr(advert_date,1,10) BETWEEN ? AND ?
        GROUP BY substr(advert_date,1,10)
        HAVING SUM(sum_price) > 0
    )
    ''', (telegram_id, prev_from, prev_to))
    row = cur.fetchone()
    conn.close()

    prev_drr = float(row[0]) if row and row[0] is not None else None
    if today_rows <= 0 or today_rev <= 0 or prev_drr is None:
        return None, None
    today_drr = today_spend / today_rev * 100
    return round(today_drr, 1), round(prev_drr, 1)


def _legacy_build_ceo_summary_v5(telegram_id, label='today'):
    days = 1 if label == 'today' else 7
    st = get_profit_stats(days, telegram_id)
    ad = get_advertising_stats(days, telegram_id)
    top = get_top_product(telegram_id)
    roi = get_roi(days, telegram_id)
    cost_stats = get_cost_fill_stats(days, telegram_id)
    roi_text = f"{roi:.1f}%" if roi is not None else "не рассчитан"
    footer = ""
    if cost_stats['all_missing']:
        footer = "\n⚠ Себестоимость не заполнена."
    elif cost_stats['partial_missing']:
        footer = "\n⚠ Себестоимость заполнена не у всех товаров."
    return (
        f"👑 CEO-отчёт ({'сегодня' if days == 1 else 'неделя'})\n\n"
        f"К выплате: {st[2]:,.2f} ₽\n"
        f"Чистая прибыль: {st[10]:,.2f} ₽\n"
        f"ROI: {roi_text}\n"
        f"Маржа: {st[11]:.1f}%\n"
        f"Реклама: {ad[4]:,.2f} ₽ | ДРР {ad[8]:.1f}%\n"
        f"Лидер: {top[0] if top else '-'}"
        f"{footer}"
    ).replace(',', ' ')


def _legacy_build_alerts_for_user_v4(telegram_id):
    settings = _get_notification_settings(telegram_id)
    alerts = []

    low_rows = [
        r for r in get_stock_forecast(telegram_id, 7, 30)
        if (r['qty'] or 0) <= settings['low_stock_threshold'] or (r['days_left'] or 999) <= 3
    ]
    low_rows = [r for r in low_rows if not _alert_key_sent(telegram_id, f"low_stock:{telegram_id}:{r['article']}")]
    if low_rows:
        sample = '\n'.join(f"{r['article']}: остаток {r['qty']}, дней {r['days_left']}" for r in low_rows[:5])
        alerts.append((
            [f"low_stock:{telegram_id}:{r['article']}" for r in low_rows],
            "📦 Заканчиваются товары\n\n" + sample
        ))

    today_drr, prev_drr = _recent_drr_change(telegram_id)
    if (
        today_drr is not None
        and prev_drr is not None
        and today_drr >= settings['drr_alert_threshold']
        and today_drr > prev_drr + 10
        and not _alert_key_sent(telegram_id, f'drr_growth:{telegram_id}')
    ):
        alerts.append((
            [f'drr_growth:{telegram_id}'],
            f"📣 Резко вырос ДРР\n\nСейчас: {today_drr:.1f}%\nСредний ДРР за 7 дней: {prev_drr:.1f}%"
        ))

    sales_drop = _sales_drop_percent(telegram_id)
    if (
        sales_drop is not None
        and sales_drop >= settings['sales_drop_threshold']
        and not _alert_key_sent(telegram_id, f'sales_drop:{telegram_id}')
    ):
        alerts.append((
            [f'sales_drop:{telegram_id}'],
            f"📉 Упали продажи\n\nПадение среднего дневного payout: {sales_drop:.1f}%"
        ))

    if settings['negative_profit_alert']:
        bad = [r for r in get_worst_profit_products(7, 5, telegram_id) if (r[10] or 0) < 0]
        bad = [r for r in bad if not _alert_key_sent(telegram_id, f"negative_margin:{telegram_id}:{r[0]}")]
        if bad:
            sample = '\n'.join(f"{r[0]}: маржа {r[10]:.1f}% | прибыль {r[9]:,.2f} ₽".replace(',', ' ') for r in bad[:5])
            alerts.append((
                [f"negative_margin:{telegram_id}:{r[0]}" for r in bad],
                "⚠ Отрицательная маржа\n\n" + sample
            ))

    return alerts


async def _legacy_alerts_job_v4(context):
    for telegram_id in _get_notified_users():
        try:
            for keys, text in _build_alerts_for_user(telegram_id):
                await context.bot.send_message(telegram_id, text)
                for key in keys:
                    _mark_alert_key(telegram_id, key, text[:500])
        except Exception as e:
            print('ALERTS_ERROR', telegram_id, e)


def _build_alerts_for_user(telegram_id):
    # Compatibility wrapper kept intentionally after duplicate cleanup.
    return _legacy_build_alerts_for_user_v4(telegram_id)


async def alerts_job(context):
    # Restore the runtime job name expected by schedule_background_jobs().
    return await _legacy_alerts_job_v4(context)


def _build_ceo_summary(telegram_id, label='today'):
    days = 1 if label == 'today' else 7
    st = get_profit_stats(days, telegram_id)
    after_tax = get_profit_stats_after_tax(days, telegram_id)
    ad = get_advertising_stats(days, telegram_id)
    top = get_top_product(telegram_id)
    roi = get_roi(days, telegram_id)
    cost_stats = get_cost_fill_stats(days, telegram_id)
    roi_text = f"{roi:.1f}%" if roi is not None else "не рассчитан"
    footer = []
    if cost_stats['all_missing']:
        footer.append("⚠ Себестоимость не заполнена.")
    elif cost_stats['partial_missing']:
        footer.append("⚠ Себестоимость заполнена не у всех товаров.")
    if after_tax['tax_warning']:
        footer.append("⚠ Налоговая система не настроена. Прибыль показана до налога.")
    footer.extend(after_tax['tax_notes'])
    footer.append(f"Налоговый режим: {format_tax_settings_label(telegram_id)}")
    footer.append("Расчёт налога предварительный. Для официальной отчётности сверяйтесь с бухгалтером.")
    tail = ('\n' + '\n'.join(footer)) if footer else ''
    return (
        f"📒 CEO-отчёт ({'сегодня' if days == 1 else 'неделя'})\n\n"
        f"К выплате: {st[2]:,.2f} ₽\n"
        f"Прибыль до налога: {after_tax['profit_before_tax']:,.2f} ₽\n"
        f"Налог: {after_tax['tax']:,.2f} ₽\n"
        f"Чистая прибыль после налога: {after_tax['profit_after_tax']:,.2f} ₽\n"
        f"ROI: {roi_text}\n"
        f"Маржа: {st[11]:.1f}%\n"
        f"Маржа после налога: {after_tax['margin_after_tax']:.1f}%\n"
        f"Реклама: {ad[4]:,.2f} ₽ | ДРР {ad[8]:.1f}%\n"
        f"Лидер: {top[0] if top else '-'}"
        f"{tail}"
    ).replace(',', ' ')
