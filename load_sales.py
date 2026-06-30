import sqlite3
import json
import os
import logging
import traceback
from collections import defaultdict
from datetime import datetime, timedelta
from time import sleep
import httpx

from config import WB_TOKEN, DB_NAME
from db_manager import init_db, _is_readonly_db_error
from update_log import save_update

STAT_API = 'https://statistics-api.wildberries.ru'
AD_API = 'https://advert-api.wildberries.ru'
ADS_PROGRESS_FILE = os.path.join(os.path.dirname(__file__), '.ads_progress.json')
ADS_BACKGROUND_STATE_FILE = os.path.join(os.path.dirname(__file__), '.ads_background_state.json')
KNOWN_ADVERT_IDS_FILE = os.path.join(os.path.dirname(__file__), '.known_advert_ids.json')
SALES_HISTORICAL_CACHE_MAX_AGE_HOURS = 6
ADS_HISTORICAL_CACHE_MAX_AGE_HOURS = 6
ADS_SAFE_MIN_COOLDOWN_SECONDS = 90 * 60
_LAST_ADS_RUN_DETAILS = {}
_LAST_COOLDOWN_WRITE = {}
logger = logging.getLogger(__name__)


def _headers(token):
    return {'Authorization': token}


def _load_ads_progress_map():
    try:
        with open(ADS_PROGRESS_FILE, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_ads_progress_map(data):
    with open(ADS_PROGRESS_FILE, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=True, indent=2)


def _get_ads_progress(telegram_id):
    return (_load_ads_progress_map().get(str(int(telegram_id or 0))) or {}).copy()


def _set_ads_progress(telegram_id, progress):
    data = _load_ads_progress_map()
    data[str(int(telegram_id or 0))] = dict(progress or {})
    _save_ads_progress_map(data)


def _clear_ads_progress(telegram_id):
    data = _load_ads_progress_map()
    data.pop(str(int(telegram_id or 0)), None)
    _save_ads_progress_map(data)


def _load_ads_background_state_map():
    try:
        with open(ADS_BACKGROUND_STATE_FILE, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _load_known_advert_ids_map():
    try:
        with open(KNOWN_ADVERT_IDS_FILE, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_known_advert_ids_map(data):
    with open(KNOWN_ADVERT_IDS_FILE, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=True, indent=2, sort_keys=True)


def _save_ads_background_state_map(data):
    with open(ADS_BACKGROUND_STATE_FILE, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=True, indent=2)


def _sales_historical_cache_path(start_date, end_date):
    safe_start = str(start_date or '').strip()
    safe_end = str(end_date or '').strip()
    return os.path.join(os.path.dirname(__file__), f'.sales_historical_cache_{safe_start}_{safe_end}.json')


def _historical_sales_rows_debug(rows):
    rows_list = list(rows or [])
    unique_sale_ids = set()
    unique_srids = set()
    sum_price = 0.0
    for row in rows_list:
        if not isinstance(row, dict):
            continue
        sale_id = str(row.get('saleID') or '').strip()
        srid = str(row.get('srid') or '').strip()
        if sale_id:
            unique_sale_ids.add(sale_id)
        if srid:
            unique_srids.add(srid)
        try:
            sum_price += float(row.get('price_with_disc') or 0)
        except Exception:
            continue
    return {
        'rows_total': int(len(rows_list)),
        'unique_saleID': int(len(unique_sale_ids)),
        'unique_srid': int(len(unique_srids)),
        'sum_price': round(sum_price, 2),
    }


def _historical_sales_debug_mismatches(expected_debug, actual_debug):
    expected_debug = dict(expected_debug or {})
    actual_debug = dict(actual_debug or {})
    mismatches = []
    for key in ('rows_total', 'unique_saleID', 'unique_srid'):
        if int(expected_debug.get(key) or 0) != int(actual_debug.get(key) or 0):
            mismatches.append(f'{key}_mismatch')
    if round(float(expected_debug.get('sum_price') or 0), 2) != round(float(actual_debug.get('sum_price') or 0), 2):
        mismatches.append('sum_price_mismatch')
    return mismatches


def _build_sales_historical_cache_payload(telegram_id, start_date, end_date, rows, api_sum_price):
    source_rows = list(rows or [])
    source_debug = _historical_sales_rows_debug(source_rows)
    payload = {
        'metadata': {
            'start_date': str(start_date),
            'end_date': str(end_date),
            'rows_after_filter': int(len(source_rows)),
            'api_sum_price': round(float(api_sum_price or 0), 2),
            'created_at': _dt(),
            'user_id': int(telegram_id or 0),
            'cache_rows_total': int(source_debug.get('rows_total') or 0),
            'cache_unique_saleID': int(source_debug.get('unique_saleID') or 0),
            'cache_unique_srid': int(source_debug.get('unique_srid') or 0),
            'cache_sum_price': round(float(source_debug.get('sum_price') or 0), 2),
        },
        'rows': source_rows,
    }
    serialized_payload = json.loads(json.dumps(payload, ensure_ascii=False))
    cache_rows = list(serialized_payload.get('rows') or [])
    cache_metadata = dict(serialized_payload.get('metadata') or {})
    cache_debug = _historical_sales_rows_debug(cache_rows)
    mismatches = _historical_sales_debug_mismatches(source_debug, cache_debug)
    status = 'CACHE_BUILD_MISMATCH' if mismatches else 'SUCCESS'
    return {
        'status': status,
        'payload': serialized_payload,
        'metadata': cache_metadata,
        'source_debug': source_debug,
        'cache_debug': cache_debug,
        'mismatches': mismatches,
    }


def _save_sales_historical_cache(telegram_id, start_date, end_date, rows, api_sum_price):
    built = _build_sales_historical_cache_payload(telegram_id, start_date, end_date, rows, api_sum_price)
    payload = built.get('payload') or {}
    path = _sales_historical_cache_path(start_date, end_date)
    if built.get('status') != 'SUCCESS':
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            logger.exception('Failed to remove outdated sales historical cache file %s after build mismatch', path)
        return {
            'status': built.get('status') or 'CACHE_BUILD_MISMATCH',
            'saved': False,
            'path': path,
            'file_size': os.path.getsize(path) if os.path.exists(path) else 0,
            'metadata': payload.get('metadata') or {},
            'source_debug': built.get('source_debug') or {},
            'cache_debug': built.get('cache_debug') or {},
            'saved_cache_debug': {},
            'mismatches': list(built.get('mismatches') or []),
            'write_compare': {},
        }
    tmp_path = f'{path}.tmp'
    if os.path.exists(tmp_path):
        try:
            os.remove(tmp_path)
        except Exception:
            pass
    try:
        with open(tmp_path, 'w', encoding='utf-8') as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
    saved_cache = _read_sales_historical_cache(telegram_id, start_date, end_date)
    saved_rows = list(saved_cache.get('rows') or [])
    saved_cache_debug = _historical_sales_rows_debug(saved_rows)
    write_mismatches = _historical_sales_debug_mismatches(built.get('cache_debug') or {}, saved_cache_debug)
    if list(payload.get('rows') or []) != saved_rows:
        write_mismatches.append('rows_payload_mismatch')
    write_compare = {
        'prepared_rows': int((built.get('cache_debug') or {}).get('rows_total') or 0),
        'saved_cache_rows': int(saved_cache_debug.get('rows_total') or 0),
    }
    file_size = int(saved_cache.get('file_size') or (os.path.getsize(path) if os.path.exists(path) else 0) or 0)
    if write_mismatches:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            logger.exception('Failed to remove mismatched sales historical cache file %s', path)
        return {
            'status': 'CACHE_WRITE_MISMATCH',
            'saved': False,
            'path': path,
            'file_size': file_size,
            'metadata': payload.get('metadata') or {},
            'source_debug': built.get('source_debug') or {},
            'cache_debug': built.get('cache_debug') or {},
            'saved_cache_debug': saved_cache_debug,
            'mismatches': write_mismatches,
            'write_compare': write_compare,
        }
    return {
        'status': 'SUCCESS',
        'saved': True,
        'path': path,
        'file_size': file_size,
        'metadata': payload.get('metadata') or {},
        'source_debug': built.get('source_debug') or {},
        'cache_debug': built.get('cache_debug') or {},
        'saved_cache_debug': saved_cache_debug,
        'mismatches': [],
        'write_compare': write_compare,
    }


def _read_sales_historical_cache(telegram_id, start_date, end_date, max_age_hours=SALES_HISTORICAL_CACHE_MAX_AGE_HOURS):
    path = _sales_historical_cache_path(start_date, end_date)
    result = {
        'path': path,
        'exists': False,
        'is_fresh': False,
        'is_valid': False,
        'file_size': 0,
        'metadata': {},
        'rows': [],
    }
    if not os.path.exists(path):
        return result
    result['exists'] = True
    try:
        result['file_size'] = int(os.path.getsize(path) or 0)
    except Exception:
        result['file_size'] = 0
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            payload = json.load(fh)
    except Exception:
        return result
    metadata = payload.get('metadata') if isinstance(payload, dict) else {}
    rows = payload.get('rows') if isinstance(payload, dict) else []
    if not isinstance(metadata, dict) or not isinstance(rows, list):
        return result
    result['metadata'] = metadata
    result['rows'] = rows
    created_at = str(metadata.get('created_at') or '').strip()
    cache_user_id = metadata.get('user_id')
    cache_start = str(metadata.get('start_date') or '')
    cache_end = str(metadata.get('end_date') or '')
    try:
        created_dt = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
        age_ok = datetime.now() - created_dt <= timedelta(hours=max_age_hours)
    except Exception:
        age_ok = False
    user_ok = int(cache_user_id or 0) == int(telegram_id or 0)
    period_ok = cache_start == str(start_date) and cache_end == str(end_date)
    row_count_ok = int(metadata.get('cache_rows_total') or len(rows or [])) == int(len(rows or []))
    sum_price_ok = round(float(metadata.get('cache_sum_price') or 0), 2) == round(float(_historical_sales_rows_debug(rows).get('sum_price') or 0), 2)
    result['is_fresh'] = bool(age_ok)
    result['is_valid'] = bool(age_ok and user_ok and period_ok and row_count_ok and sum_price_ok)
    return result


def _ads_historical_cache_path(start_date, end_date):
    safe_start = str(start_date or '').strip()
    safe_end = str(end_date or '').strip()
    return os.path.join(os.path.dirname(__file__), f'.ads_historical_cache_{safe_start}_{safe_end}.json')


def _historical_ads_rows_debug(rows, field='nm_id'):
    stats = _historical_ads_count_nm(rows, field=field)
    rows_with_supplier_article = 0
    for row in rows or []:
        article = str((row or {}).get('supplier_article') or '').strip()
        if article:
            rows_with_supplier_article += 1
    return {
        **stats,
        'rows_total': int(stats.get('rows_count') or 0),
        'rows_with_supplier_article': int(rows_with_supplier_article),
    }


def _historical_ads_debug_mismatches(expected_debug, actual_debug):
    expected_debug = dict(expected_debug or {})
    actual_debug = dict(actual_debug or {})
    mismatches = []
    for key in ('rows_total', 'positive_nm_id', 'negative_nm_id', 'null_nm_id', 'rows_with_supplier_article'):
        if int(expected_debug.get(key) or 0) != int(actual_debug.get(key) or 0):
            mismatches.append(f'{key}_mismatch')
    return mismatches


def _build_ads_historical_cache_payload(telegram_id, start_date, end_date, rows, metadata):
    source_rows = list(rows or [])
    source_debug = _historical_ads_rows_debug(source_rows, field='nm_id')
    payload = {
        'metadata': {
            'start_date': str(start_date),
            'end_date': str(end_date),
            'rows_after_filter': int(len(source_rows)),
            'created_at': _dt(),
            'user_id': int(telegram_id or 0),
            **dict(metadata or {}),
        },
        'rows': source_rows,
    }
    payload['metadata']['cache_positive_nm_id'] = int(source_debug.get('positive_nm_id') or 0)
    payload['metadata']['cache_supplier_article_count'] = int(source_debug.get('rows_with_supplier_article') or 0)
    payload['metadata']['cache_linkability'] = round(float(payload['metadata'].get('projected_linkability') or 0), 1)

    serialized_payload = json.loads(json.dumps(payload, ensure_ascii=False))
    cache_rows = list(serialized_payload.get('rows') or [])
    cache_metadata = dict(serialized_payload.get('metadata') or {})
    cache_debug = _historical_ads_rows_debug(cache_rows, field='nm_id')

    mismatches = []
    if int(source_debug.get('positive_nm_id') or 0) > 0 and int(cache_debug.get('positive_nm_id') or 0) <= 0:
        mismatches.append('positive_nm_id_lost_after_serialization')

    status = 'CACHE_BUILD_MISMATCH' if mismatches else 'SUCCESS'
    return {
        'status': status,
        'payload': serialized_payload,
        'metadata': cache_metadata,
        'source_debug': source_debug,
        'cache_debug': cache_debug,
        'mismatches': mismatches,
    }


def _save_ads_historical_cache(telegram_id, start_date, end_date, rows, metadata):
    built = _build_ads_historical_cache_payload(telegram_id, start_date, end_date, rows, metadata)
    payload = built.get('payload') or {}
    path = _ads_historical_cache_path(start_date, end_date)
    if built.get('status') != 'SUCCESS':
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            logger.exception('Failed to remove outdated ads historical cache file %s after build mismatch', path)
        return {
            'status': built.get('status') or 'CACHE_BUILD_MISMATCH',
            'saved': False,
            'path': path,
            'file_size': os.path.getsize(path) if os.path.exists(path) else 0,
            'metadata': payload.get('metadata') or {},
            'source_debug': built.get('source_debug') or {},
            'cache_debug': built.get('cache_debug') or {},
            'saved_cache_debug': {},
            'mismatches': list(built.get('mismatches') or []),
            'write_compare': {},
        }
    tmp_path = f'{path}.tmp'
    if os.path.exists(tmp_path):
        try:
            os.remove(tmp_path)
        except Exception:
            pass
    try:
        with open(tmp_path, 'w', encoding='utf-8') as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
    saved_cache = _read_ads_historical_cache(telegram_id, start_date, end_date)
    saved_rows = list(saved_cache.get('rows') or [])
    saved_cache_debug = _historical_ads_rows_debug(saved_rows, field='nm_id')
    write_mismatches = _historical_ads_debug_mismatches(built.get('cache_debug') or {}, saved_cache_debug)
    if list(payload.get('rows') or []) != saved_rows:
        write_mismatches.append('rows_payload_mismatch')
    write_compare = {
        'prepared_rows': int((built.get('cache_debug') or {}).get('rows_total') or 0),
        'saved_cache_rows': int(saved_cache_debug.get('rows_total') or 0),
    }
    file_size = int(saved_cache.get('file_size') or (os.path.getsize(path) if os.path.exists(path) else 0) or 0)
    if write_mismatches:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            logger.exception('Failed to remove mismatched ads historical cache file %s', path)
        return {
            'status': 'CACHE_WRITE_MISMATCH',
            'saved': False,
            'path': path,
            'file_size': file_size,
            'metadata': payload.get('metadata') or {},
            'source_debug': built.get('source_debug') or {},
            'cache_debug': built.get('cache_debug') or {},
            'saved_cache_debug': saved_cache_debug,
            'mismatches': write_mismatches,
            'write_compare': write_compare,
        }
    return {
        'status': 'SUCCESS',
        'saved': True,
        'path': path,
        'file_size': file_size,
        'metadata': payload.get('metadata') or {},
        'source_debug': built.get('source_debug') or {},
        'cache_debug': built.get('cache_debug') or {},
        'saved_cache_debug': saved_cache_debug,
        'mismatches': [],
        'write_compare': write_compare,
    }


def _read_ads_historical_cache(telegram_id, start_date, end_date, max_age_hours=ADS_HISTORICAL_CACHE_MAX_AGE_HOURS):
    path = _ads_historical_cache_path(start_date, end_date)
    result = {
        'path': path,
        'exists': False,
        'is_fresh': False,
        'is_valid': False,
        'file_size': 0,
        'metadata': {},
        'rows': [],
    }
    if not os.path.exists(path):
        return result
    result['exists'] = True
    try:
        result['file_size'] = int(os.path.getsize(path) or 0)
    except Exception:
        result['file_size'] = 0
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            payload = json.load(fh)
    except Exception:
        return result
    metadata = payload.get('metadata') if isinstance(payload, dict) else {}
    rows = payload.get('rows') if isinstance(payload, dict) else []
    if not isinstance(metadata, dict) or not isinstance(rows, list):
        return result
    result['metadata'] = metadata
    result['rows'] = rows
    created_at = str(metadata.get('created_at') or '').strip()
    cache_user_id = metadata.get('user_id')
    cache_start = str(metadata.get('start_date') or '')
    cache_end = str(metadata.get('end_date') or '')
    try:
        created_dt = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
        age_ok = datetime.now() - created_dt <= timedelta(hours=max_age_hours)
    except Exception:
        age_ok = False
    user_ok = int(cache_user_id or 0) == int(telegram_id or 0)
    period_ok = cache_start == str(start_date) and cache_end == str(end_date)
    result['is_fresh'] = bool(age_ok)
    result['is_valid'] = bool(age_ok and user_ok and period_ok)
    return result


def _get_ads_background_state(telegram_id):
    return (_load_ads_background_state_map().get(str(int(telegram_id or 0))) or {}).copy()


def _set_ads_background_state(telegram_id, state):
    data = _load_ads_background_state_map()
    data[str(int(telegram_id or 0))] = dict(state or {})
    _save_ads_background_state_map(data)


def _get_known_advert_ids(telegram_id):
    known = []
    seen = set()
    data = _load_known_advert_ids_map()
    file_ids = (data.get(str(int(telegram_id or 0))) or {}).get('advert_ids') or []
    for value in file_ids:
        try:
            advert_id = int(value)
        except Exception:
            continue
        if advert_id not in seen:
            seen.add(advert_id)
            known.append(advert_id)

    init_db()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        '''
        SELECT DISTINCT campaign_id
        FROM advertising
        WHERE telegram_id=? AND campaign_id IS NOT NULL AND TRIM(CAST(campaign_id AS TEXT))!=''
        ORDER BY campaign_id
        ''',
        (telegram_id,),
    )
    for row in cur.fetchall():
        try:
            advert_id = int(row[0])
        except Exception:
            continue
        if advert_id not in seen:
            seen.add(advert_id)
            known.append(advert_id)

    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('campaigns', 'advertising_campaigns', 'ad_campaigns') ORDER BY name"
    )
    campaign_tables = [str(row[0]) for row in cur.fetchall() if row and row[0]]
    for table_name in campaign_tables:
        for column_name in ('campaign_id', 'advert_id', 'advertId', 'id'):
            try:
                cur.execute(
                    f"SELECT DISTINCT {column_name} FROM {table_name} WHERE {column_name} IS NOT NULL AND TRIM(CAST({column_name} AS TEXT))!='' ORDER BY {column_name}"
                )
            except Exception:
                continue
            for row in cur.fetchall():
                try:
                    advert_id = int(row[0])
                except Exception:
                    continue
                if advert_id not in seen:
                    seen.add(advert_id)
                    known.append(advert_id)
            break
    conn.close()
    return known


def _remember_known_advert_ids(telegram_id, advert_ids):
    normalized = []
    seen = set()
    for value in advert_ids or []:
        try:
            advert_id = int(value)
        except Exception:
            continue
        if advert_id in seen:
            continue
        seen.add(advert_id)
        normalized.append(advert_id)
    data = _load_known_advert_ids_map()
    data[str(int(telegram_id or 0))] = {
        'advert_ids': normalized,
        'updated_at': _now_str(),
    }
    _save_known_advert_ids_map(data)


def _merge_advert_id_sources(*sources):
    merged = []
    seen = set()
    for source in sources:
        for value in source or []:
            try:
                advert_id = int(value)
            except Exception:
                continue
            if advert_id in seen:
                continue
            seen.add(advert_id)
            merged.append(advert_id)
    return merged


def _acquire_local_sync_lock(telegram_id, sync_block, max_age_minutes=30):
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT started_at FROM sync_locks WHERE telegram_id=? AND sync_block=?', (telegram_id, sync_block))
    row = cur.fetchone()
    now = _now_dt()
    if row and row[0]:
        started_at = _parse_dt(row[0])
        if started_at and now - started_at < timedelta(minutes=max_age_minutes):
            conn.close()
            return False
    cur.execute('DELETE FROM sync_locks WHERE telegram_id=? AND sync_block=?', (telegram_id, sync_block))
    cur.execute(
        'INSERT INTO sync_locks(telegram_id,sync_block,started_at) VALUES(?,?,?)',
        (telegram_id, sync_block, now.strftime('%Y-%m-%d %H:%M:%S'))
    )
    conn.commit()
    conn.close()
    return True


def _release_local_sync_lock(telegram_id, sync_block):
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('DELETE FROM sync_locks WHERE telegram_id=? AND sync_block=?', (telegram_id, sync_block))
    conn.commit()
    conn.close()


def _set_last_ads_run_details(telegram_id, details):
    _LAST_ADS_RUN_DETAILS[int(telegram_id or 0)] = dict(details or {})


def _get_last_ads_run_details(telegram_id):
    return (_LAST_ADS_RUN_DETAILS.get(int(telegram_id or 0)) or {}).copy()


def _prev_date(date_text):
    return (datetime.strptime(str(date_text), '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')


def _ads_dates_desc(days):
    total_days = max(1, int(days or 1))
    end_dt = datetime.strptime(_today(), '%Y-%m-%d')
    return [
        (end_dt - timedelta(days=offset)).strftime('%Y-%m-%d')
        for offset in range(total_days)
    ]


def _normalize_ads_progress(progress, days=None):
    data = dict(progress or {})
    if not data:
        return {}
    try:
        total_dates = int(data.get('total_dates') or 0)
    except Exception:
        total_dates = 0
    if total_dates <= 0:
        date_from = str(data.get('date_from') or '')
        date_to = str(data.get('date_to') or '')
        if date_from and date_to:
            try:
                from_dt = datetime.strptime(date_from, '%Y-%m-%d')
                to_dt = datetime.strptime(date_to, '%Y-%m-%d')
                total_dates = max(1, int((to_dt - from_dt).days) + 1)
            except Exception:
                total_dates = max(1, int(days or 1))
        else:
            total_dates = max(1, int(days or 1))
    try:
        current_date_index = int(data.get('current_date_index'))
    except Exception:
        current_date = str(data.get('current_date') or '')
        date_to = str(data.get('date_to') or '')
        if current_date and date_to:
            try:
                current_date_index = max(0, int((datetime.strptime(date_to, '%Y-%m-%d') - datetime.strptime(current_date, '%Y-%m-%d')).days))
            except Exception:
                current_date_index = 0
        else:
            current_date_index = 0
    try:
        current_campaign_index = int(data.get('current_campaign_index'))
    except Exception:
        current_campaign_index = int(data.get('campaign_index') or 0)
    data['total_dates'] = total_dates
    data['current_date_index'] = max(0, current_date_index)
    data['current_campaign_index'] = max(0, current_campaign_index)
    return data


def get_ads_progress_snapshot(telegram_id, days=None):
    progress = _normalize_ads_progress(_get_ads_progress(telegram_id), days=days)
    if not progress:
        return {}
    total_dates = max(1, int(progress.get('total_dates') or days or 1))
    current_date_index = max(0, int(progress.get('current_date_index') or 0))
    current_campaign_index = max(0, int(progress.get('current_campaign_index') or 0))
    return {
        'date_from': progress.get('date_from'),
        'date_to': progress.get('date_to'),
        'total_dates': total_dates,
        'current_date_index': current_date_index,
        'current_campaign_index': current_campaign_index,
        'current_date_number': min(total_dates, current_date_index + 1),
        'completed_dates': min(total_dates, current_date_index),
        'is_active': True,
    }


def is_ads_period_partially_loaded(telegram_id, days):
    snapshot = get_ads_progress_snapshot(telegram_id, days=days)
    if not snapshot:
        return False
    required_days = max(1, int(days or snapshot.get('total_dates') or 1))
    return int(snapshot.get('completed_dates') or 0) < min(required_days, int(snapshot.get('total_dates') or required_days))


def _token_kind(token):
    text = str(token or '').strip()
    if not text:
        return 'empty'
    parts = text.split('.')
    if len(parts) == 3:
        return 'jwt'
    return f'non-jwt:{len(parts)}-segments'


def _token_preview(token):
    text = str(token or '').strip()
    return {
        'length': len(text),
        'prefix': text[:10] if text else '',
        'suffix': text[-10:] if text else '',
    }


def _remember_cooldown_write(telegram_id, api_block, caller, status, retry_seconds, saved_until):
    _LAST_COOLDOWN_WRITE[(int(telegram_id or 0), str(api_block or ''))] = {
        'caller': caller,
        'status': status,
        'retry_seconds': retry_seconds,
        'saved_until': saved_until,
        'current_time': _now_str(),
    }


def get_last_cooldown_write_details(telegram_id, api_block):
    return (_LAST_COOLDOWN_WRITE.get((int(telegram_id or 0), str(api_block or ''))) or {}).copy()


def _log_ads_token_debug(token, source='unknown'):
    preview = _token_preview(token)
    print('ADS TOKEN DEBUG')
    print('source=', source)
    print('length=', preview['length'])
    print('prefix=', preview['prefix'])
    print('suffix=', preview['suffix'])
    print('type=', _token_kind(token))


def _retry(resp):
    retry = resp.headers.get('x-ratelimit-retry') or resp.headers.get('X-Ratelimit-Retry') or 'неизвестно'
    return f'RATE_LIMIT:{retry}'


def _status_code(status):
    if not status:
        return 'unknown'
    parts = str(status).split(':', 1)
    tail = parts[1] if len(parts) > 1 else parts[0]
    return tail.split(':', 1)[0]


def _is_ad_url(url):
    return 'advert-api.wildberries.ru' in str(url or '')


def _log_ads_request(method, url, params=None, body=None):
    if not _is_ad_url(url):
        return
    print('ADS REQUEST:')
    print('method=', method)
    print('url=', url)
    print('params=', params)
    print('body=', body)


def _log_ads_response(url, resp=None, error=None):
    if not _is_ad_url(url):
        return
    print('ADS RESPONSE:')
    if error is not None:
        print('error=', repr(error))
        return
    print('status_code=', resp.status_code)
    print('headers=', dict(resp.headers))
    print('text=', (resp.text or '')[:2000])


def _log_ads_fullstats(url, params, status, payload=None):
    print('ADS FULLSTATS:')
    print('url=', url)
    print('params=', params)
    print('status=', status)
    if payload is not None:
        text = str(payload)
        print('sample=', text[:1000])


def _header_value(headers, *names):
    for name in names:
        value = headers.get(name)
        if value not in (None, ''):
            return value
    return None


def _is_finance_report_detail_url(url):
    return 'statistics-api.wildberries.ru' in str(url or '') and 'reportDetailByPeriod' in str(url or '')


def _log_finance_rate_limit_debug(caller, resp=None, computed_retry_after=None, saved_until=None):
    now_str = _now_str()
    print('FINANCE RATE LIMIT DEBUG')
    print('caller=', caller)
    print('http_status=', resp.status_code if resp is not None else 'unknown')
    print('retry_after_header=', _header_value(resp.headers, 'Retry-After', 'retry-after') if resp is not None else None)
    print('x_ratelimit_retry=', _header_value(resp.headers, 'X-Ratelimit-Retry', 'x-ratelimit-retry') if resp is not None else None)
    print('x_ratelimit_reset=', _header_value(resp.headers, 'X-Ratelimit-Reset', 'x-ratelimit-reset') if resp is not None else None)
    print('computed_retry_after=', computed_retry_after)
    print('saved_until=', saved_until)
    print('current_time=', now_str)


def _log_ads_cooldown_debug(status, retry_after=None, saved_until=None, now=None, remaining=None):
    print('ADS COOLDOWN DEBUG')
    print('status=', status)
    print('retry_after=', retry_after)
    print('saved_until=', saved_until)
    print('now=', now)
    print('remaining=', remaining)


def _log_ads_cooldown_write(caller, status, retry_after=None, saved_until=None):
    print('ADS COOLDOWN WRITE')
    print('caller=', caller)
    print('status=', status)
    print('retry_after=', retry_after)
    print('saved_until=', saved_until)


def _log_ads_exception(exc):
    print('ADS EXCEPTION')
    print('type=', type(exc).__name__)
    print('message=', str(exc))
    print('traceback=')
    print(traceback.format_exc())


def _log_ads_exception_wrapper(caller, exc):
    print('ADS EXCEPTION WRAPPER')
    print('caller=', caller)
    print('type=', type(exc).__name__)
    print('message=', str(exc))
    print('traceback=')
    print(traceback.format_exc())


def _fullstats_retry_seconds(resp):
    raw_retry = _header_value(
        resp.headers,
        'Retry-After',
        'retry-after',
        'X-Ratelimit-Retry',
        'x-ratelimit-retry',
    )
    if raw_retry in (None, ''):
        return None
    try:
        return max(0, int(float(raw_retry)))
    except Exception:
        return None


def _fullstats_safe_cooldown_seconds(resp):
    retry_seconds = _fullstats_retry_seconds(resp)
    if retry_seconds is None:
        return ADS_SAFE_MIN_COOLDOWN_SECONDS
    return max(ADS_SAFE_MIN_COOLDOWN_SECONDS, retry_seconds + 30 * 60)


def _log_fullstats_first_request(stage, campaign_ids, begin, end, resp=None):
    print('ADS FULLSTATS FIRST REQUEST:')
    print('stage=', stage)
    print('campaign_ids=', [int(x) for x in campaign_ids if x is not None])
    print('campaign_ids_count=', len([x for x in campaign_ids if x is not None]))
    print('beginDate=', begin)
    print('endDate=', end)
    if resp is None:
        return
    print('http_status=', resp.status_code)
    print('retry_after=', _header_value(resp.headers, 'Retry-After', 'retry-after'))
    print('x_ratelimit_retry=', _header_value(resp.headers, 'X-Ratelimit-Retry', 'x-ratelimit-retry'))
    print('x_ratelimit_reset=', _header_value(resp.headers, 'X-Ratelimit-Reset', 'x-ratelimit-reset'))
    print('response_first_500_chars=', (resp.text or '')[:500])


def _get(url, token, params=None, timeout=60, token_source='unknown', caller='unknown'):
    try:
        resp = httpx.get(url, headers=_headers(token), params=params, timeout=timeout)
    except httpx.TimeoutException as e:
        return None, 'TIMEOUT'
    except Exception as e:
        return None, 'CONNECTION_ERROR'
    if resp.status_code == 429:
        if _is_finance_report_detail_url(url):
            retry_raw = _header_value(resp.headers, 'Retry-After', 'retry-after', 'X-Ratelimit-Retry', 'x-ratelimit-retry')
            try:
                retry_seconds = max(0, int(float(retry_raw)))
            except Exception:
                retry_seconds = None
            saved_until = (_now_dt() + timedelta(seconds=retry_seconds)).strftime('%Y-%m-%d %H:%M:%S') if retry_seconds is not None else None
            _log_finance_rate_limit_debug(caller=caller, resp=resp, computed_retry_after=retry_seconds, saved_until=saved_until)
        return None, _retry(resp)
    if resp.status_code != 200:
        return None, f'ERROR_{resp.status_code}'
    try:
        return resp.json(), 'SUCCESS'
    except Exception:
        return None, 'INVALID_JSON'


def _post(url, token, body=None, timeout=90, token_source='unknown'):
    try:
        resp = httpx.post(url, headers=_headers(token), json=body, timeout=timeout)
    except httpx.TimeoutException as e:
        return None, 'TIMEOUT'
    except Exception as e:
        return None, 'CONNECTION_ERROR'
    if resp.status_code == 429:
        return None, _retry(resp)
    if resp.status_code not in (200, 201, 204):
        return None, f'ERROR_{resp.status_code}'
    try:
        return resp.json() if resp.content else [], 'SUCCESS'
    except Exception:
        return None, 'INVALID_JSON'


def _num(value):
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def _int(value):
    try:
        return int(float(value or 0))
    except Exception:
        return 0


def _date_from(days):
    try:
        days = int(days or 0)
    except Exception:
        days = 0
    days = max(1, days)
    return (datetime.now() - timedelta(days=days - 1)).strftime('%Y-%m-%d')


def _today():
    return datetime.now().strftime('%Y-%m-%d')


def _normalize_period_dates(days):
    if isinstance(days, tuple) and len(days) == 2:
        return str(days[0]), str(days[1])
    return _date_from(days), _today()


def _dt():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _date_only(value):
    text = str(value or '').strip()
    return text[:10] if text else ''


def _in_range(date_text, start_date, end_date):
    day = _date_only(date_text)
    if not day:
        return False
    return str(start_date) <= day <= str(end_date)


def _first(row, names, default=None):
    for name in names:
        if isinstance(row, dict) and row.get(name) not in (None, ''):
            return row.get(name)
    return default


def _sales_row_identity(telegram_id, row):
    raw = row.get('saleID') or row.get('srid') or f"{row.get('date')}:{row.get('supplierArticle')}:{row.get('nmId')}:{row.get('forPay')}"
    return {
        'raw_key': str(raw),
        'primary_key': f'{telegram_id}:{raw}',
        'strategy': 'saleID -> srid -> date:supplierArticle:nmId:forPay',
    }


def _orders_row_identity(telegram_id, row):
    raw = row.get('odid') or row.get('srid') or f"{row.get('date')}:{row.get('supplierArticle')}:{row.get('nmId')}:{row.get('totalPrice')}"
    return {
        'raw_key': str(raw),
        'primary_key': f'{telegram_id}:{raw}',
        'strategy': 'odid -> srid -> date:supplierArticle:nmId:totalPrice',
    }


def _summarize_api_rows(rows, telegram_id, start_date, end_date, kind='sales'):
    filtered_rows = []
    day_map = defaultdict(lambda: {'count': 0, 'sum': 0.0})
    article_map = defaultdict(lambda: {'count': 0, 'sum': 0.0})
    seen_ids = set()
    duplicate_keys = 0
    min_date = None
    max_date = None
    raw_min_date = None
    raw_max_date = None
    min_last_change = None
    max_last_change = None
    raw_min_last_change = None
    raw_max_last_change = None
    last_change_present = 0
    raw_row_date_samples = []
    raw_last_change_samples = []
    id_builder = _sales_row_identity if kind == 'sales' else _orders_row_identity
    amount_field = 'priceWithDisc'
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        row_date = _date_only(row.get('date'))
        if row_date:
            raw_min_date = row_date if raw_min_date is None or row_date < raw_min_date else raw_min_date
            raw_max_date = row_date if raw_max_date is None or row_date > raw_max_date else raw_max_date
            if len(raw_row_date_samples) < 5:
                raw_row_date_samples.append(row_date)
        last_change = _date_only(_first(row, ['lastChangeDate', 'last_change_date', 'lastChangeDateTime']))
        if last_change:
            raw_min_last_change = last_change if raw_min_last_change is None or last_change < raw_min_last_change else raw_min_last_change
            raw_max_last_change = last_change if raw_max_last_change is None or last_change > raw_max_last_change else raw_max_last_change
            if len(raw_last_change_samples) < 5:
                raw_last_change_samples.append(last_change)
        if not _in_range(row_date, start_date, end_date):
            continue
        filtered_rows.append(row)
        identity = id_builder(telegram_id, row)
        if identity['primary_key'] in seen_ids:
            duplicate_keys += 1
        else:
            seen_ids.add(identity['primary_key'])
        amount = _num(row.get(amount_field))
        day_map[row_date]['count'] += 1
        day_map[row_date]['sum'] += amount
        article = str(row.get('supplierArticle') or '-').strip() or '-'
        article_map[article]['count'] += 1
        article_map[article]['sum'] += amount
        if row_date:
            min_date = row_date if min_date is None or row_date < min_date else min_date
            max_date = row_date if max_date is None or row_date > max_date else max_date
        if last_change:
            last_change_present += 1
            min_last_change = last_change if min_last_change is None or last_change < min_last_change else min_last_change
            max_last_change = last_change if max_last_change is None or last_change > max_last_change else max_last_change
    return {
        'filtered_rows': filtered_rows,
        'received_rows': len([row for row in rows or [] if isinstance(row, dict)]),
        'rows_in_range': len(filtered_rows),
        'pages_loaded': 1,
        'pagination_used': False,
        'next_value': None,
        'limit_value': None,
        'flag_value': None,
        'last_change_param': None,
        'min_date': min_date,
        'max_date': max_date,
        'raw_min_date': raw_min_date,
        'raw_max_date': raw_max_date,
        'min_last_change_date': min_last_change,
        'max_last_change_date': max_last_change,
        'raw_min_last_change_date': raw_min_last_change,
        'raw_max_last_change_date': raw_max_last_change,
        'rows_with_last_change_date': last_change_present,
        'filter_date_field': 'date',
        'filter_condition': '_in_range(_date_only(row[date]), start_date, end_date)',
        'raw_row_date_samples': raw_row_date_samples,
        'raw_last_change_date_samples': raw_last_change_samples,
        'unique_primary_keys': len(seen_ids),
        'duplicate_computed_keys': duplicate_keys,
        'day_groups': [
            {'date': date_value, 'count': values['count'], 'sum': round(values['sum'], 2)}
            for date_value, values in sorted(day_map.items())
        ],
        'article_groups': [
            {'supplier_article': article, 'count': values['count'], 'sum': round(values['sum'], 2)}
            for article, values in sorted(article_map.items(), key=lambda item: (-item[1]['count'], -item[1]['sum'], item[0]))
        ],
        'identity_strategy': id_builder(telegram_id, filtered_rows[0])['strategy'] if filtered_rows else id_builder(telegram_id, {'date': '', 'supplierArticle': '', 'nmId': '', 'forPay': '', 'totalPrice': ''})['strategy'],
        'sample_primary_key': id_builder(telegram_id, filtered_rows[0])['primary_key'] if filtered_rows else None,
    }


def inspect_sales_api(token, start_date, end_date, telegram_id=0):
    params = {'dateFrom': str(start_date)}
    payload, status = _get(
        f'{STAT_API}/api/v1/supplier/sales',
        token,
        params,
        caller='inspect_sales_api->supplier/sales'
    )
    if status != 'SUCCESS':
        return {
            'kind': 'sales',
            'status': status,
            'api': f'{STAT_API}/api/v1/supplier/sales',
            'params': {'dateFrom': str(start_date), 'flag': None, 'lastChangeDate': None, 'limit': None, 'next': None},
            'pages_loaded': 0,
            'pagination_used': False,
            'received_rows': 0,
            'rows_in_range': 0,
            'filtered_rows': [],
        }
    if not isinstance(payload, list):
        return {
            'kind': 'sales',
            'status': 'INVALID_RESPONSE',
            'api': f'{STAT_API}/api/v1/supplier/sales',
            'params': {'dateFrom': str(start_date), 'flag': None, 'lastChangeDate': None, 'limit': None, 'next': None},
            'pages_loaded': 0,
            'pagination_used': False,
            'received_rows': 0,
            'rows_in_range': 0,
            'filtered_rows': [],
        }
    summary = _summarize_api_rows(payload, telegram_id, start_date, end_date, kind='sales')
    summary.update({
        'kind': 'sales',
        'status': 'SUCCESS',
        'api': f'{STAT_API}/api/v1/supplier/sales',
        'params': {'dateFrom': str(start_date), 'flag': None, 'lastChangeDate': None, 'limit': None, 'next': None},
    })
    return summary


def inspect_orders_api(token, start_date, end_date, telegram_id=0):
    params = {'dateFrom': str(start_date)}
    payload, status = _get(
        f'{STAT_API}/api/v1/supplier/orders',
        token,
        params,
        caller='inspect_orders_api->supplier/orders'
    )
    if status != 'SUCCESS':
        return {
            'kind': 'orders',
            'status': status,
            'api': f'{STAT_API}/api/v1/supplier/orders',
            'params': {'dateFrom': str(start_date), 'flag': None, 'lastChangeDate': None, 'limit': None, 'next': None},
            'pages_loaded': 0,
            'pagination_used': False,
            'received_rows': 0,
            'rows_in_range': 0,
            'filtered_rows': [],
        }
    if not isinstance(payload, list):
        return {
            'kind': 'orders',
            'status': 'INVALID_RESPONSE',
            'api': f'{STAT_API}/api/v1/supplier/orders',
            'params': {'dateFrom': str(start_date), 'flag': None, 'lastChangeDate': None, 'limit': None, 'next': None},
            'pages_loaded': 0,
            'pagination_used': False,
            'received_rows': 0,
            'rows_in_range': 0,
            'filtered_rows': [],
        }
    summary = _summarize_api_rows(payload, telegram_id, start_date, end_date, kind='orders')
    summary.update({
        'kind': 'orders',
        'status': 'SUCCESS',
        'api': f'{STAT_API}/api/v1/supplier/orders',
        'params': {'dateFrom': str(start_date), 'flag': None, 'lastChangeDate': None, 'limit': None, 'next': None},
    })
    return summary


def _persist_sales_rows(cur, telegram_id, rows):
    stats = {'inserted': 0, 'updated': 0, 'skipped': 0, 'invalid': 0}
    for row in rows or []:
        if not isinstance(row, dict):
            stats['invalid'] += 1
            continue
        identity = _sales_row_identity(telegram_id, row)
        sale_id = identity['primary_key']
        for_pay = _num(row.get('forPay'))
        is_return = 1 if str(identity['raw_key']).startswith('R') or for_pay < 0 else 0
        new_values = (
            str(row.get('date') or ''),
            row.get('supplierArticle'),
            row.get('nmId'),
            row.get('barcode'),
            row.get('warehouseName'),
            row.get('category'),
            row.get('brand'),
            _num(row.get('totalPrice')),
            for_pay,
            _num(row.get('finishedPrice')),
            _num(row.get('priceWithDisc')),
            is_return,
        )
        cur.execute(
            "SELECT sale_date,supplier_article,nm_id,barcode,warehouse_name,category,brand,total_price,for_pay,finished_price,price_with_disc,is_return "
            "FROM sales WHERE sale_id=?",
            (sale_id,)
        )
        existing = cur.fetchone()
        if existing is None:
            cur.execute(
                '''
                INSERT INTO sales (
                    sale_id, telegram_id, sale_date, supplier_article, nm_id, barcode,
                    warehouse_name, category, brand, total_price, for_pay,
                    finished_price, price_with_disc, is_return
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (sale_id, telegram_id, *new_values)
            )
            stats['inserted'] += 1
        elif tuple(existing) == tuple(new_values):
            stats['skipped'] += 1
        else:
            cur.execute(
                '''
                UPDATE sales
                SET sale_date=?, supplier_article=?, nm_id=?, barcode=?, warehouse_name=?,
                    category=?, brand=?, total_price=?, for_pay=?, finished_price=?,
                    price_with_disc=?, is_return=?
                WHERE sale_id=?
                ''',
                (*new_values, sale_id)
            )
            stats['updated'] += 1
    return stats


def _persist_orders_rows(cur, telegram_id, rows):
    stats = {'inserted': 0, 'updated': 0, 'skipped': 0, 'invalid': 0}
    for row in rows or []:
        if not isinstance(row, dict):
            stats['invalid'] += 1
            continue
        identity = _orders_row_identity(telegram_id, row)
        order_id = identity['primary_key']
        is_cancel = 1 if row.get('isCancel') in (True, 1, 'true', 'True') else 0
        new_values = (
            str(row.get('date') or ''),
            row.get('supplierArticle'),
            row.get('nmId'),
            row.get('barcode'),
            row.get('warehouseName'),
            row.get('category'),
            row.get('brand'),
            _num(row.get('totalPrice')),
            _num(row.get('finishedPrice')),
            _num(row.get('priceWithDisc')),
            is_cancel,
            row.get('cancelDate'),
        )
        cur.execute(
            "SELECT order_date,supplier_article,nm_id,barcode,warehouse_name,category,brand,total_price,finished_price,price_with_disc,is_cancel,cancel_date "
            "FROM orders WHERE order_id=?",
            (order_id,)
        )
        existing = cur.fetchone()
        if existing is None:
            cur.execute(
                '''
                INSERT INTO orders (
                    order_id, telegram_id, order_date, supplier_article, nm_id, barcode,
                    warehouse_name, category, brand, total_price, finished_price,
                    price_with_disc, is_cancel, cancel_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (order_id, telegram_id, *new_values)
            )
            stats['inserted'] += 1
        elif tuple(existing) == tuple(new_values):
            stats['skipped'] += 1
        else:
            cur.execute(
                '''
                UPDATE orders
                SET order_date=?, supplier_article=?, nm_id=?, barcode=?, warehouse_name=?,
                    category=?, brand=?, total_price=?, finished_price=?, price_with_disc=?,
                    is_cancel=?, cancel_date=?
                WHERE order_id=?
                ''',
                (*new_values, order_id)
            )
            stats['updated'] += 1
    return stats


def estimate_sales_orders_backfill_impact(telegram_id, sales_rows, orders_rows):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        sales_stats = {'inserted': 0, 'updated': 0, 'skipped': 0, 'invalid': 0}
        for row in sales_rows or []:
            if not isinstance(row, dict):
                sales_stats['invalid'] += 1
                continue
            identity = _sales_row_identity(telegram_id, row)
            sale_id = identity['primary_key']
            for_pay = _num(row.get('forPay'))
            is_return = 1 if str(identity['raw_key']).startswith('R') or for_pay < 0 else 0
            new_values = (
                str(row.get('date') or ''),
                row.get('supplierArticle'),
                row.get('nmId'),
                row.get('barcode'),
                row.get('warehouseName'),
                row.get('category'),
                row.get('brand'),
                _num(row.get('totalPrice')),
                for_pay,
                _num(row.get('finishedPrice')),
                _num(row.get('priceWithDisc')),
                is_return,
            )
            cur.execute(
                "SELECT sale_date,supplier_article,nm_id,barcode,warehouse_name,category,brand,total_price,for_pay,finished_price,price_with_disc,is_return "
                "FROM sales WHERE sale_id=?",
                (sale_id,)
            )
            existing = cur.fetchone()
            if existing is None:
                sales_stats['inserted'] += 1
            elif tuple(existing) == tuple(new_values):
                sales_stats['skipped'] += 1
            else:
                sales_stats['updated'] += 1

        orders_stats = {'inserted': 0, 'updated': 0, 'skipped': 0, 'invalid': 0}
        for row in orders_rows or []:
            if not isinstance(row, dict):
                orders_stats['invalid'] += 1
                continue
            identity = _orders_row_identity(telegram_id, row)
            order_id = identity['primary_key']
            is_cancel = 1 if row.get('isCancel') in (True, 1, 'true', 'True') else 0
            new_values = (
                str(row.get('date') or ''),
                row.get('supplierArticle'),
                row.get('nmId'),
                row.get('barcode'),
                row.get('warehouseName'),
                row.get('category'),
                row.get('brand'),
                _num(row.get('totalPrice')),
                _num(row.get('finishedPrice')),
                _num(row.get('priceWithDisc')),
                is_cancel,
                row.get('cancelDate'),
            )
            cur.execute(
                "SELECT order_date,supplier_article,nm_id,barcode,warehouse_name,category,brand,total_price,finished_price,price_with_disc,is_cancel,cancel_date "
                "FROM orders WHERE order_id=?",
                (order_id,)
            )
            existing = cur.fetchone()
            if existing is None:
                orders_stats['inserted'] += 1
            elif tuple(existing) == tuple(new_values):
                orders_stats['skipped'] += 1
            else:
                orders_stats['updated'] += 1
        return {'sales': sales_stats, 'orders': orders_stats}
    finally:
        conn.close()


def _estimate_sales_backfill_readonly(telegram_id, sales_rows, start_date=None, end_date=None):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        stats = {
            'inserted': 0,
            'updated': 0,
            'skipped': 0,
            'invalid': 0,
            'missing_in_local_db': 0,
            'sum_insert': 0.0,
            'sum_update_delta': 0.0,
            'unique_saleID': 0,
            'unique_srid': 0,
        }
        saleid_seen = set()
        srid_seen = set()
        day_decisions = defaultdict(lambda: {'would_insert': 0, 'would_update': 0, 'would_skip': 0, 'sum_price': 0.0})
        for row in sales_rows or []:
            if not isinstance(row, dict):
                stats['invalid'] += 1
                continue
            sale_id_value = row.get('saleID')
            srid_value = row.get('srid')
            if sale_id_value not in (None, ''):
                saleid_seen.add(str(sale_id_value))
            if srid_value not in (None, ''):
                srid_seen.add(str(srid_value))
            identity = _sales_row_identity(telegram_id, row)
            sale_id = identity['primary_key']
            for_pay = _num(row.get('forPay'))
            is_return = 1 if str(identity['raw_key']).startswith('R') or for_pay < 0 else 0
            new_values = (
                str(row.get('date') or ''),
                row.get('supplierArticle'),
                row.get('nmId'),
                row.get('barcode'),
                row.get('warehouseName'),
                row.get('category'),
                row.get('brand'),
                _num(row.get('totalPrice')),
                for_pay,
                _num(row.get('finishedPrice')),
                _num(row.get('priceWithDisc')),
                is_return,
            )
            row_day = _date_only(row.get('date'))
            cur.execute(
                "SELECT sale_date,supplier_article,nm_id,barcode,warehouse_name,category,brand,total_price,for_pay,finished_price,price_with_disc,is_return "
                "FROM sales WHERE sale_id=?",
                (sale_id,),
            )
            existing = cur.fetchone()
            new_sum = float(new_values[10] or 0)
            day_decisions[row_day]['sum_price'] += new_sum
            if existing is None:
                stats['inserted'] += 1
                stats['missing_in_local_db'] += 1
                stats['sum_insert'] += new_sum
                day_decisions[row_day]['would_insert'] += 1
            elif tuple(existing) == tuple(new_values):
                stats['skipped'] += 1
                day_decisions[row_day]['would_skip'] += 1
            else:
                stats['updated'] += 1
                stats['sum_update_delta'] += new_sum - float(existing[10] or 0)
                day_decisions[row_day]['would_update'] += 1
        stats['unique_saleID'] = len(saleid_seen)
        stats['unique_srid'] = len(srid_seen)
        current_snapshot = {'min_date': None, 'max_date': None, 'rows': 0, 'sum_price': 0.0}
        if start_date is not None and end_date is not None:
            cur.execute(
                "SELECT MIN(substr(sale_date,1,10)), MAX(substr(sale_date,1,10)), COUNT(*), COALESCE(SUM(price_with_disc),0) "
                "FROM sales WHERE telegram_id=? AND substr(sale_date,1,10) BETWEEN ? AND ?",
                (telegram_id, str(start_date), str(end_date))
            )
            snapshot_row = cur.fetchone() or (None, None, 0, 0)
            current_snapshot = {
                'min_date': snapshot_row[0],
                'max_date': snapshot_row[1],
                'rows': int(snapshot_row[2] or 0),
                'sum_price': round(float(snapshot_row[3] or 0), 2),
            }
        projected_snapshot = {
            'min_date': current_snapshot.get('min_date') or (str(start_date) if sales_rows else None),
            'max_date': current_snapshot.get('max_date') or (str(end_date) if sales_rows else None),
            'rows': int(current_snapshot.get('rows') or 0) + int(stats['inserted'] or 0),
            'sum_price': round(float(current_snapshot.get('sum_price') or 0) + float(stats['sum_insert'] or 0) + float(stats['sum_update_delta'] or 0), 2),
        }
        days = []
        for day_value in sorted(day_decisions):
            item = day_decisions[day_value]
            days.append({
                'day': day_value,
                'would_insert': int(item['would_insert'] or 0),
                'would_update': int(item['would_update'] or 0),
                'would_skip': int(item['would_skip'] or 0),
                'sum_price': round(float(item['sum_price'] or 0), 2),
            })
        return {
            'sales': stats,
            'current_snapshot': current_snapshot,
            'projected_snapshot': projected_snapshot,
            'days': days,
        }
    finally:
        conn.close()


def backfill_sales_orders_range(telegram_id, token, start_date, end_date):
    sales_api = inspect_sales_api(token, start_date, end_date, telegram_id)
    orders_api = inspect_orders_api(token, start_date, end_date, telegram_id)
    result = {
        'range_start': str(start_date),
        'range_end': str(end_date),
        'sales_api': sales_api,
        'orders_api': orders_api,
        'status': 'SUCCESS',
        'sales_db': {'inserted': 0, 'updated': 0, 'skipped': 0, 'invalid': 0},
        'orders_db': {'inserted': 0, 'updated': 0, 'skipped': 0, 'invalid': 0},
    }
    if sales_api.get('status') != 'SUCCESS' or orders_api.get('status') != 'SUCCESS':
        result['status'] = f"SALES:{sales_api.get('status')}|ORDERS:{orders_api.get('status')}"
        return result

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        sales_stats = _persist_sales_rows(cur, telegram_id, sales_api.get('filtered_rows') or [])
        orders_stats = _persist_orders_rows(cur, telegram_id, orders_api.get('filtered_rows') or [])
        cur.execute(
            '''
            INSERT OR IGNORE INTO products (telegram_id, supplier_article, cost_price, last_price)
            SELECT ?, supplier_article, 0, MAX(price_with_disc)
            FROM sales
            WHERE telegram_id=? AND supplier_article IS NOT NULL
            GROUP BY supplier_article
            ''',
            (telegram_id, telegram_id)
        )
        conn.commit()
        result['sales_db'] = sales_stats
        result['orders_db'] = orders_stats
    except Exception as exc:
        conn.rollback()
        result['status'] = f'EXCEPTION:{type(exc).__name__}'
    finally:
        conn.close()

    logger.info(
        'SALES BACKFILL user=%s range=%s..%s sales_api_received=%s sales_in_range=%s sales_inserted=%s sales_updated=%s sales_skipped=%s '
        'orders_api_received=%s orders_in_range=%s orders_inserted=%s orders_updated=%s orders_skipped=%s status=%s',
        telegram_id,
        start_date,
        end_date,
        sales_api.get('received_rows'),
        sales_api.get('rows_in_range'),
        result['sales_db'].get('inserted'),
        result['sales_db'].get('updated'),
        result['sales_db'].get('skipped'),
        orders_api.get('received_rows'),
        orders_api.get('rows_in_range'),
        result['orders_db'].get('inserted'),
        result['orders_db'].get('updated'),
        result['orders_db'].get('skipped'),
        result['status'],
    )
    return result


def historical_sales_backfill(telegram_id, token, start_date, end_date):
    sales_api = inspect_sales_api(token, start_date, end_date, telegram_id)
    result = {
        'status': 'SUCCESS',
        'start_date': str(start_date),
        'end_date': str(end_date),
        'raw_filtered_rows': list(sales_api.get('filtered_rows') or []),
        'cache': {
            'saved': False,
            'path': _sales_historical_cache_path(start_date, end_date),
            'created_at': None,
        },
        'days': [],
        'totals': {
            'received': 0,
            'inserted': 0,
            'updated': 0,
            'skipped': 0,
            'invalid': 0,
            'sum_price': 0.0,
            'rows_before_filter': 0,
            'rows_after_filter': 0,
            'unique_saleID': 0,
            'unique_srid': 0,
            'would_insert': 0,
            'would_update': 0,
            'would_skip': 0,
            'missing_in_local_db': 0,
            'projected_sales_count': 0,
            'projected_sales_sum': 0.0,
        },
        'sales_snapshot': {'min_date': None, 'max_date': None, 'rows': 0, 'sum_price': 0.0},
        'projected_sales_snapshot': {'min_date': None, 'max_date': None, 'rows': 0, 'sum_price': 0.0},
        'api_audit': {
            'status': sales_api.get('status'),
            'date_from': str(start_date),
            'total_received': int(sales_api.get('received_rows', 0) or 0),
            'rows_before_filter': int(sales_api.get('received_rows', 0) or 0),
            'rows_after_filter': int(sales_api.get('rows_in_range', 0) or 0),
            'min_date': sales_api.get('raw_min_date'),
            'max_date': sales_api.get('raw_max_date'),
            'filter_date_field': sales_api.get('filter_date_field'),
            'filter_condition': sales_api.get('filter_condition'),
            'row_date_samples': list(sales_api.get('raw_row_date_samples') or []),
            'last_change_date_samples': list(sales_api.get('raw_last_change_date_samples') or []),
        },
    }
    if sales_api.get('status') != 'SUCCESS':
        result['status'] = sales_api.get('status')
        logger.info(
            'HISTORICAL SALES BATCH AUDIT user=%s range=%s..%s status=%s total_received=0 rows_after_filter=0 zero_code_line=%s',
            telegram_id,
            start_date,
            end_date,
            result['status'],
            'load_sales.py:722-733',
        )
        return result

    impact = _estimate_sales_backfill_readonly(
        telegram_id,
        sales_api.get('filtered_rows') or [],
        start_date=start_date,
        end_date=end_date,
    )
    sales_stats = impact.get('sales') or {}
    days = []
    for item in impact.get('days') or []:
        day_value = str(item.get('day') or '')
        days.append({
            'day': day_value,
            'status': sales_api.get('status'),
            'received': int(item.get('would_insert', 0) or 0) + int(item.get('would_update', 0) or 0) + int(item.get('would_skip', 0) or 0),
            'rows_after_period_filter': int(item.get('would_insert', 0) or 0) + int(item.get('would_update', 0) or 0) + int(item.get('would_skip', 0) or 0),
            'first_row_date': day_value or None,
            'last_row_date': day_value or None,
            'filter_date_field': sales_api.get('filter_date_field'),
            'filter_condition': sales_api.get('filter_condition'),
            'row_date_samples': [day_value] if day_value else [],
            'first_last_change_date': None,
            'last_last_change_date': None,
            'last_change_date_samples': [],
            'zero_stage': 'rows grouped locally after one batch API call',
            'zero_code_line': 'load_sales.py:1120-1139',
            'inserted': int(item.get('would_insert', 0) or 0),
            'updated': int(item.get('would_update', 0) or 0),
            'skipped': int(item.get('would_skip', 0) or 0),
            'would_insert': int(item.get('would_insert', 0) or 0),
            'would_update': int(item.get('would_update', 0) or 0),
            'would_skip': int(item.get('would_skip', 0) or 0),
            'sum_price': round(float(item.get('sum_price') or 0), 2),
        })

    totals = {
        'received': int(sales_api.get('received_rows', 0) or 0),
        'inserted': int(sales_stats.get('inserted', 0) or 0),
        'updated': int(sales_stats.get('updated', 0) or 0),
        'skipped': int(sales_stats.get('skipped', 0) or 0),
        'invalid': int(sales_stats.get('invalid', 0) or 0),
        'sum_price': round(sum(float(item.get('sum_price', 0) or 0) for item in days), 2),
        'rows_before_filter': int(sales_api.get('received_rows', 0) or 0),
        'rows_after_filter': int(sales_api.get('rows_in_range', 0) or 0),
        'unique_saleID': int(sales_stats.get('unique_saleID', 0) or 0),
        'unique_srid': int(sales_stats.get('unique_srid', 0) or 0),
        'would_insert': int(sales_stats.get('inserted', 0) or 0),
        'would_update': int(sales_stats.get('updated', 0) or 0),
        'would_skip': int(sales_stats.get('skipped', 0) or 0),
        'missing_in_local_db': int(sales_stats.get('missing_in_local_db', 0) or 0),
        'projected_sales_count': int((impact.get('projected_snapshot') or {}).get('rows', 0) or 0),
        'projected_sales_sum': round(float((impact.get('projected_snapshot') or {}).get('sum_price', 0) or 0), 2),
    }
    result.update({
        'days': days,
        'totals': totals,
        'sales_snapshot': impact.get('current_snapshot') or result['sales_snapshot'],
        'projected_sales_snapshot': impact.get('projected_snapshot') or result['projected_sales_snapshot'],
    })
    try:
        cache_info = _save_sales_historical_cache(
            telegram_id,
            start_date,
            end_date,
            result.get('raw_filtered_rows') or [],
            totals.get('sum_price') or 0,
        )
        result['cache'] = {
            'saved': bool(cache_info.get('saved')),
            'path': cache_info.get('path'),
            'created_at': (cache_info.get('metadata') or {}).get('created_at'),
        }
        if cache_info.get('status') != 'SUCCESS':
            result['status'] = cache_info.get('status') or 'CACHE_WRITE_MISMATCH'
    except Exception:
        logger.exception('Failed to save sales historical cache user=%s range=%s..%s', telegram_id, start_date, end_date)
    logger.info(
        'HISTORICAL SALES BATCH AUDIT user=%s range=%s..%s status=%s total_received=%s rows_before_filter=%s rows_after_filter=%s '
        'min_date=%s max_date=%s unique_saleID=%s unique_srid=%s would_insert=%s would_update=%s would_skip=%s current_rows=%s projected_rows=%s current_sum=%s projected_sum=%s',
        telegram_id,
        start_date,
        end_date,
        result['status'],
        totals.get('received'),
        totals.get('rows_before_filter'),
        totals.get('rows_after_filter'),
        result['api_audit'].get('min_date'),
        result['api_audit'].get('max_date'),
        totals.get('unique_saleID'),
        totals.get('unique_srid'),
        totals.get('would_insert'),
        totals.get('would_update'),
        totals.get('would_skip'),
        result['sales_snapshot'].get('rows'),
        result['projected_sales_snapshot'].get('rows'),
        result['sales_snapshot'].get('sum_price'),
        result['projected_sales_snapshot'].get('sum_price'),
    )
    return result


def _sales_period_snapshot(telegram_id, start_date, end_date):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT
                MIN(substr(sale_date,1,10)),
                MAX(substr(sale_date,1,10)),
                COUNT(*),
                COALESCE(SUM(price_with_disc), 0)
            FROM sales
            WHERE telegram_id=? AND substr(sale_date,1,10) BETWEEN ? AND ?
            """,
            (telegram_id, str(start_date), str(end_date)),
        )
        row = cur.fetchone() or (None, None, 0, 0)
        return {
            'min_date': row[0],
            'max_date': row[1],
            'rows': int(row[2] or 0),
            'sum_price': round(float(row[3] or 0), 2),
        }
    finally:
        conn.close()


def apply_historical_sales_backfill(telegram_id, token, start_date, end_date):
    db_before = _sales_period_snapshot(telegram_id, start_date, end_date)
    cache = _read_sales_historical_cache(telegram_id, start_date, end_date)
    cache_metadata = cache.get('metadata') or {}
    cached_rows = list(cache.get('rows') or [])
    result = {
        'status': 'SUCCESS',
        'start_date': str(start_date),
        'end_date': str(end_date),
        'historical': None,
        'cache_used': 'no',
        'cache_created_at': cache_metadata.get('created_at'),
        'cache_path': cache.get('path'),
        'api': {
            'total_received': int(cache_metadata.get('rows_after_filter') or 0),
            'rows_after_filter': int(cache_metadata.get('rows_after_filter') or 0),
            'api_sum_price': round(float(cache_metadata.get('api_sum_price') or 0), 2),
        },
        'db_before': db_before,
        'apply': {
            'inserted': 0,
            'updated': 0,
            'skipped': 0,
            'invalid': 0,
            'errors': 0,
        },
        'db_after': db_before,
        'expected': {
            'rows': int(cache_metadata.get('rows_after_filter') or 0),
            'sum_price': round(float(cache_metadata.get('api_sum_price') or 0), 2),
        },
        'delta': {
            'rows_delta': int(db_before.get('rows') or 0) - int(cache_metadata.get('rows_after_filter') or 0),
            'sum_delta': round(float(db_before.get('sum_price') or 0) - float(cache_metadata.get('api_sum_price') or 0), 2),
        },
        'guards': {
            'status_success': False,
            'rows_after_filter_positive': False,
            'would_insert_positive': False,
            'api_sum_gt_local_sum': False,
        },
        'guard_failures': [],
        'write_performed': False,
    }
    if not cache.get('is_valid'):
        result['status'] = 'CACHE_MISSING_OR_EXPIRED'
        return result

    impact = _estimate_sales_backfill_readonly(
        telegram_id,
        cached_rows,
        start_date=start_date,
        end_date=end_date,
    )
    sales_stats = impact.get('sales') or {}
    totals = {
        'rows_after_filter': int(cache_metadata.get('rows_after_filter') or 0),
        'sum_price': round(float(cache_metadata.get('api_sum_price') or 0), 2),
        'would_insert': int(sales_stats.get('inserted') or 0),
        'would_update': int(sales_stats.get('updated') or 0),
        'would_skip': int(sales_stats.get('skipped') or 0),
    }
    result = {
        **result,
        'cache_used': 'yes',
        'api': {
            'total_received': int(cache_metadata.get('rows_after_filter') or 0),
            'rows_after_filter': int(totals.get('rows_after_filter') or 0),
            'api_sum_price': round(float(totals.get('sum_price') or 0), 2),
        },
        'expected': {
            'rows': int(totals.get('rows_after_filter') or 0),
            'sum_price': round(float(totals.get('sum_price') or 0), 2),
        },
        'delta': {
            'rows_delta': int(db_before.get('rows') or 0) - int(totals.get('rows_after_filter') or 0),
            'sum_delta': round(float(db_before.get('sum_price') or 0) - float(totals.get('sum_price') or 0), 2),
        },
        'guards': {
            'status_success': True,
            'rows_after_filter_positive': int(totals.get('rows_after_filter') or 0) > 0,
            'would_insert_positive': int(totals.get('would_insert') or 0) > 0,
            'api_sum_gt_local_sum': float(totals.get('sum_price') or 0) > float(db_before.get('sum_price') or 0),
        },
    }

    if not result['guards']['status_success']:
        result['guard_failures'].append('status != SUCCESS')
    if not result['guards']['rows_after_filter_positive']:
        result['guard_failures'].append('rows_after_filter <= 0')
    if not result['guards']['would_insert_positive']:
        result['guard_failures'].append('would_insert <= 0')
    if not result['guards']['api_sum_gt_local_sum']:
        result['guard_failures'].append('api_sum_price <= local_sum')

    if result['guard_failures']:
        result['status'] = 'GUARD_BLOCKED'
        return result

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        stats = _persist_sales_rows(cur, telegram_id, cached_rows)
        conn.commit()
        db_after = _sales_period_snapshot(telegram_id, start_date, end_date)
        result['apply'] = {
            'inserted': int(stats.get('inserted') or 0),
            'updated': int(stats.get('updated') or 0),
            'skipped': int(stats.get('skipped') or 0),
            'invalid': int(stats.get('invalid') or 0),
            'errors': 0,
        }
        result['db_after'] = db_after
        result['delta'] = {
            'rows_delta': int(db_after.get('rows') or 0) - int(result['expected'].get('rows') or 0),
            'sum_delta': round(float(db_after.get('sum_price') or 0) - float(result['expected'].get('sum_price') or 0), 2),
        }
        result['status'] = 'SUCCESS'
        result['write_performed'] = True
    except Exception as exc:
        conn.rollback()
        result['status'] = f'EXCEPTION:{type(exc).__name__}'
        result['apply']['errors'] = 1
    finally:
        conn.close()
    logger.info(
        'APPLY HISTORICAL SALES user=%s range=%s..%s status=%s cache_used=%s cache_created_at=%s rows_after_filter=%s inserted=%s updated=%s skipped=%s invalid=%s errors=%s before_rows=%s after_rows=%s before_sum=%s after_sum=%s',
        telegram_id,
        start_date,
        end_date,
        result.get('status'),
        result.get('cache_used'),
        result.get('cache_created_at'),
        result['api'].get('rows_after_filter'),
        result['apply'].get('inserted'),
        result['apply'].get('updated'),
        result['apply'].get('skipped'),
        result['apply'].get('invalid'),
        result['apply'].get('errors'),
        result['db_before'].get('rows'),
        result['db_after'].get('rows'),
        result['db_before'].get('sum_price'),
        result['db_after'].get('sum_price'),
    )
    return result


def historical_advertising_backfill(telegram_id, token, start_date, end_date):
    init_db()
    result = {
        'status': 'SUCCESS',
        'start_date': str(start_date),
        'end_date': str(end_date),
        'cache': {
            'saved': False,
            'path': _ads_historical_cache_path(start_date, end_date),
            'created_at': None,
        },
        'prepared_rows_check': {
            'rows_count': 0,
            'positive_nm_id': 0,
            'negative_nm_id': 0,
            'null_nm_id': 0,
            'rows_with_supplier_article': 0,
        },
        'cache_debug': {
            'rows_count': 0,
            'rows_total': 0,
            'positive_nm_id': 0,
            'negative_nm_id': 0,
            'null_nm_id': 0,
            'rows_with_supplier_article': 0,
            'projected_linkability': 0.0,
        },
        'rows': [],
        'summary': {
            'campaigns_found': 0,
            'advertising_rows': 0,
            'rows_with_real_nmid': 0,
            'rows_with_placeholder_nmid': 0,
            'rows_matching_sales': 0,
            'rows_matching_products': 0,
            'projected_linkability': 0.0,
            'projected_linked_spend': 0.0,
            'projected_linked_revenue': 0.0,
            'total_spend': 0.0,
        },
        'db_before': _advertising_period_snapshot(telegram_id, start_date, end_date),
    }
    advertising_cooldown = _cooldown_status(telegram_id, 'advertising')
    if advertising_cooldown:
        result['status'] = advertising_cooldown
        return result
    fetched_ids, status = _fetch_advert_ids(token, token_source='historical_advertising_backfill')
    known_ids = _get_known_advert_ids(telegram_id)
    batch_ids = _merge_advert_id_sources(fetched_ids, known_ids)
    result['summary']['campaigns_found'] = int(len(batch_ids))
    if status != 'SUCCESS':
        result['status'] = status
        return result
    if not batch_ids:
        return result
    payload, batch_status = _fetch_fullstats_batch(token, batch_ids, str(start_date), str(end_date), timeout=120, token_source='historical_advertising_backfill')
    if batch_status != 'SUCCESS':
        result['status'] = batch_status
        return result
    conn = sqlite3.connect(DB_NAME)
    try:
        cur = conn.cursor()
        prepared = _prepare_advertising_rows(cur, telegram_id, payload)
        rows = [_advertising_tuple_to_dict(item) for item in prepared.get('parsed_rows') or []]
        prepared_debug = _historical_ads_rows_debug(rows, field='nm_id')
        metrics = _advertising_projected_metrics(cur, telegram_id, rows)
        result['rows'] = rows
        result['prepared_rows_check'] = dict(prepared_debug)
        result['summary'] = {
            'campaigns_found': int(len(batch_ids)),
            'advertising_rows': int(metrics.get('rows_after_filter') or 0),
            'rows_with_real_nmid': int(metrics.get('rows_with_real_nmid') or 0),
            'rows_with_placeholder_nmid': int(metrics.get('rows_with_placeholder_nmid') or 0),
            'rows_matching_sales': int(metrics.get('rows_matching_sales') or 0),
            'rows_matching_products': int(metrics.get('rows_matching_products') or 0),
            'projected_linkability': round(float(metrics.get('projected_linkability') or 0), 1),
            'projected_linked_spend': round(float(metrics.get('projected_linked_spend') or 0), 2),
            'projected_linked_revenue': round(float(metrics.get('projected_linked_revenue') or 0), 2),
            'total_spend': round(float(metrics.get('total_spend') or 0), 2),
        }
        cache_info = _save_ads_historical_cache(telegram_id, start_date, end_date, rows, result['summary'])
        result['cache_debug'] = {
            **dict(cache_info.get('cache_debug') or {}),
            'projected_linkability': round(float((cache_info.get('metadata') or {}).get('cache_linkability') or result['summary'].get('projected_linkability') or 0), 1),
        }
        result['cache'] = {
            'saved': bool(cache_info.get('saved')),
            'path': cache_info.get('path'),
            'file_size': int(cache_info.get('file_size') or 0),
            'created_at': (cache_info.get('metadata') or {}).get('created_at'),
            'status': cache_info.get('status') or 'SUCCESS',
            'written_rows': int((cache_info.get('saved_cache_debug') or cache_info.get('cache_debug') or {}).get('rows_total') or 0),
            'written_positive_nm_id': int((cache_info.get('saved_cache_debug') or cache_info.get('cache_debug') or {}).get('positive_nm_id') or 0),
            'written_supplier_article_count': int((cache_info.get('saved_cache_debug') or cache_info.get('cache_debug') or {}).get('rows_with_supplier_article') or 0),
            'write_compare': dict(cache_info.get('write_compare') or {}),
            'mismatches': list(cache_info.get('mismatches') or []),
        }
        if cache_info.get('status') != 'SUCCESS':
            result['status'] = cache_info.get('status') or 'CACHE_BUILD_MISMATCH'
    finally:
        conn.close()
    return result


def _historical_ads_select_top_campaigns(cur, telegram_id, start_date, end_date, limit=3):
    cur.execute(
        """
        SELECT
            CAST(campaign_id AS TEXT) AS campaign_id,
            ROUND(COALESCE(SUM(spend), 0), 2) AS spend_total,
            COUNT(*) AS rows_count,
            SUM(CASE WHEN nm_id IS NULL OR nm_id <= 0 THEN 1 ELSE 0 END) AS rows_need_fix
        FROM advertising
        WHERE telegram_id=?
          AND substr(advert_date,1,10) BETWEEN ? AND ?
          AND TRIM(COALESCE(campaign_id, ''))!=''
        GROUP BY CAST(campaign_id AS TEXT)
        ORDER BY spend_total DESC, campaign_id
        LIMIT ?
        """,
        (telegram_id, str(start_date), str(end_date), int(limit or 3)),
    )
    campaigns = []
    for row in cur.fetchall():
        campaign_id = str(row[0] or '').strip()
        if not campaign_id:
            continue
        campaigns.append({
            'campaign_id': campaign_id,
            'spend': round(float(row[1] or 0), 2),
            'rows': int(row[2] or 0),
            'rows_need_fix': int(row[3] or 0),
        })
    return campaigns


def _historical_ads_real_nm_id(value):
    try:
        if value in (None, ''):
            return None
        normalized = int(str(value).strip())
        return normalized if normalized > 0 else None
    except Exception:
        return None


def _historical_ads_count_nm(rows, field='nm_id'):
    stats = {
        'rows_count': int(len(rows or [])),
        'positive_nm_id': 0,
        'negative_nm_id': 0,
        'null_nm_id': 0,
    }
    for row in rows or []:
        value = row.get(field)
        try:
            if value in (None, ''):
                stats['null_nm_id'] += 1
                continue
            normalized = int(str(value).strip())
        except Exception:
            stats['null_nm_id'] += 1
            continue
        if normalized > 0:
            stats['positive_nm_id'] += 1
        elif normalized < 0:
            stats['negative_nm_id'] += 1
        else:
            stats['null_nm_id'] += 1
    return stats


def _historical_ads_sales_matches(cur, telegram_id, nm_ids):
    matches = {}
    unique_ids = []
    for nm_id in nm_ids or []:
        real_nm_id = _historical_ads_real_nm_id(nm_id)
        if real_nm_id is not None and real_nm_id not in unique_ids:
            unique_ids.append(real_nm_id)
    for nm_id in unique_ids:
        cur.execute(
            """
            SELECT supplier_article
            FROM sales
            WHERE telegram_id=? AND nm_id=? AND supplier_article IS NOT NULL AND TRIM(supplier_article)!=''
            LIMIT 1
            """,
            (telegram_id, nm_id),
        )
        row = cur.fetchone()
        matches[nm_id] = {
            'supplier_article': row[0] if row else _article_by_nm(cur, telegram_id, nm_id),
            'matched': row is not None,
        }
    return matches


def _historical_ads_prepare_sample(rows, fields, limit=5):
    sample = []
    for row in rows or []:
        item = {}
        for field in fields:
            item[field] = row.get(field)
        sample.append(item)
        if len(sample) >= limit:
            break
    return sample


def _historical_ads_raw_summary(cur, telegram_id, campaigns, payload):
    raw_campaigns = payload
    if isinstance(payload, dict):
        raw_campaigns = payload.get('data') or payload.get('adverts') or payload.get('campaigns') or []
    if not isinstance(raw_campaigns, list):
        raw_campaigns = []

    by_campaign_id = {}
    for campaign in raw_campaigns:
        if not isinstance(campaign, dict):
            continue
        campaign_id = campaign.get('advertId') or campaign.get('id') or campaign.get('campaignId')
        if campaign_id in (None, ''):
            continue
        by_campaign_id[str(campaign_id)] = campaign

    summary = []
    for item in campaigns or []:
        campaign_id = str(item.get('campaign_id') or '').strip()
        campaign = by_campaign_id.get(campaign_id)
        days = campaign.get('days') or campaign.get('statistics') or campaign.get('stats') or [] if isinstance(campaign, dict) else []
        if isinstance(days, dict):
            days = [days]
        elif not isinstance(days, list):
            days = []
        apps_count = 0
        raw_nms_count = 0
        unique_real_nm_ids = []
        for day in days:
            if not isinstance(day, dict):
                continue
            apps = day.get('apps') or day.get('items') or day.get('nm') or []
            if isinstance(apps, dict):
                apps = [apps]
            elif not isinstance(apps, list):
                apps = []
            apps_count += len([app for app in apps if isinstance(app, dict)])
            for app in apps:
                if not isinstance(app, dict):
                    continue
                nms = app.get('nms') or app.get('nm') or app.get('items') or []
                if isinstance(nms, dict):
                    nms = [nms]
                elif not isinstance(nms, list):
                    nms = []
                for nm_item in nms:
                    if not isinstance(nm_item, dict):
                        continue
                    raw_nms_count += 1
                    real_nm_id = _historical_ads_real_nm_id(
                        nm_item.get('nmId') or nm_item.get('nm') or nm_item.get('id')
                    )
                    if real_nm_id is not None and real_nm_id not in unique_real_nm_ids:
                        unique_real_nm_ids.append(real_nm_id)
        matches = _historical_ads_sales_matches(cur, telegram_id, unique_real_nm_ids)
        summary.append({
            'campaign_id': campaign_id,
            'raw_campaign_found': campaign is not None,
            'days_count': int(len([day for day in days if isinstance(day, dict)])),
            'apps_count': int(apps_count),
            'raw_nms_count': int(raw_nms_count),
            'raw_real_nmid_count': int(len(unique_real_nm_ids)),
            'unique_raw_real_nmids': unique_real_nm_ids,
            'matched_with_sales': [
                {
                    'nm_id': nm_id,
                    'supplier_article': (matches.get(nm_id) or {}).get('supplier_article') or '-',
                    'matched': bool((matches.get(nm_id) or {}).get('matched')),
                }
                for nm_id in unique_real_nm_ids[:10]
            ],
        })
    return summary


def _fullstats_source_total_spend(payload):
    campaigns = payload
    if isinstance(payload, dict):
        campaigns = payload.get('data') or payload.get('adverts') or payload.get('campaigns') or []
    if not isinstance(campaigns, list):
        return 0.0

    total_spend = 0.0
    for campaign in campaigns:
        if not isinstance(campaign, dict):
            continue
        campaign_spend, campaign_source = _fullstats_direct_item_spend(campaign)
        if campaign_source != 'none':
            total_spend = round(total_spend + campaign_spend, 2)
            continue
        days = campaign.get('days') or campaign.get('statistics') or campaign.get('stats') or []
        if isinstance(days, dict):
            days = [days]
        elif not isinstance(days, list):
            days = []
        day_total = 0.0
        has_day_spend = False
        app_total = 0.0
        has_app_spend = False
        item_total = 0.0
        has_item_spend = False
        for day in days:
            if not isinstance(day, dict):
                continue
            current_day_spend, current_day_source = _fullstats_direct_day_spend(day)
            if current_day_source != 'none':
                day_total = round(day_total + current_day_spend, 2)
                has_day_spend = True
            apps = day.get('apps') or day.get('items') or day.get('nm') or []
            if isinstance(apps, dict):
                apps = [apps]
            elif not isinstance(apps, list):
                apps = []
            for app in apps:
                if not isinstance(app, dict):
                    continue
                current_app_spend, current_app_source = _fullstats_direct_app_spend(app)
                if current_app_source != 'none':
                    app_total = round(app_total + current_app_spend, 2)
                    has_app_spend = True
                nms = app.get('nm') or app.get('nms') or app.get('items') or []
                if isinstance(nms, dict):
                    nms = [nms]
                elif not isinstance(nms, list):
                    nms = []
                for item in nms:
                    if not isinstance(item, dict):
                        continue
                    current_item_spend, current_item_source = _fullstats_direct_item_spend(item)
                    if current_item_source != 'none':
                        item_total = round(item_total + current_item_spend, 2)
                        has_item_spend = True
        if has_day_spend:
            total_spend = round(total_spend + day_total, 2)
        elif has_app_spend:
            total_spend = round(total_spend + app_total, 2)
        elif has_item_spend:
            total_spend = round(total_spend + item_total, 2)
    return round(total_spend, 2)


def _historical_ads_iterator_allocation_source(row):
    allocation_source = str(row.get('allocation_source') or '').strip()
    nm_id = _historical_ads_real_nm_id(row.get('nm_id'))
    spend_source = str(row.get('spend_source') or 'none').strip()
    aggregate_key = str(row.get('aggregate_key') or '').strip()
    if allocation_source == 'app':
        return 'app'
    if allocation_source == 'day':
        return 'day'
    if nm_id is not None and spend_source.startswith('item.'):
        return 'direct_nm'
    if aggregate_key.startswith(('agg_day:', 'agg_app:', 'agg_app_flat:', 'agg_day_remainder:', 'agg_app_remainder:')):
        return 'aggregate_without_nm'
    return 'unknown'


def _historical_ads_iterator_allocation_method(row):
    method = str(row.get('allocation_method') or '').strip()
    if method:
        return method
    spend_source = str(row.get('spend_source') or 'none').strip()
    nm_id = _historical_ads_real_nm_id(row.get('nm_id'))
    if nm_id is not None and spend_source.startswith('item.'):
        return 'direct'
    return 'none'


def _historical_ads_scope_key(source, campaign_id, date_value, app_type=None, app_index=None, item_index=None):
    return '|'.join((
        str(source or '-'),
        str(campaign_id or '-'),
        str(date_value or '-')[:10],
        str(app_type or '-'),
        str(app_index if app_index is not None else '-'),
        str(item_index if item_index is not None else '-'),
    ))


def _historical_ads_expected_iterator_scopes(payload):
    scopes = []
    if isinstance(payload, dict):
        payload = payload.get('data') or payload.get('adverts') or payload.get('campaigns') or []
    if not isinstance(payload, list):
        return scopes

    for campaign in payload:
        if not isinstance(campaign, dict):
            continue
        cid = campaign.get('advertId') or campaign.get('id') or campaign.get('campaignId')
        days_rows = campaign.get('days') or campaign.get('statistics') or campaign.get('stats') or [campaign]
        if not isinstance(days_rows, list):
            days_rows = [campaign]

        for day_index, day in enumerate(days_rows):
            if not isinstance(day, dict):
                continue
            d = str(day.get('date') or day.get('day') or _today())[:10]
            day_spend, day_spend_source = _fullstats_direct_day_spend(day)
            apps = day.get('apps') or day.get('items') or day.get('nm') or [day]
            if not isinstance(apps, list):
                apps = [day]
            simulated_day_rows = []

            for app_index, app in enumerate(apps):
                app_node = app if isinstance(app, dict) else day
                current_app_type = app_node.get('appType') or app_node.get('type') or app_node.get('appTypeName') or app_node.get('name')
                raw_nm_items = app_node.get('nm') or app_node.get('nms') or app_node.get('items')
                explicit_nm = raw_nm_items is not None
                if explicit_nm and not isinstance(raw_nm_items, list):
                    raw_nm_items = [raw_nm_items]
                nm_items = raw_nm_items if explicit_nm else []
                app_spend, app_spend_source = _fullstats_direct_app_spend(app_node)

                if explicit_nm:
                    simulated_app_rows = []
                    spendful_total = 0.0
                    for item_index, item in enumerate(nm_items):
                        if not isinstance(item, dict):
                            continue
                        spend, spend_source = _fullstats_direct_item_spend(item)
                        nm_id = item.get('nmId') or item.get('nm') or item.get('id')
                        real_nm_id = _historical_ads_real_nm_id(nm_id)
                        if spend_source != 'none':
                            scopes.append({
                                'scope_key': _historical_ads_scope_key('direct_nm', cid, d, current_app_type, app_index, item_index),
                                'source': 'direct_nm',
                                'campaign_id': str(cid or ''),
                                'date': d,
                                'app_type': str(current_app_type or '').strip() or None,
                                'source_spend': round(_num(spend), 2),
                            })
                            spendful_total = round(spendful_total + _num(spend), 2)
                        simulated_app_rows.append({
                            'real_nm_id': real_nm_id,
                            'spend_source': spend_source,
                            'app_type': current_app_type,
                            'app_index': app_index,
                        })

                    if app_spend_source != 'none':
                        remaining_app_spend = round(max(0.0, _num(app_spend) - spendful_total), 2)
                        app_eligible = [
                            row for row in simulated_app_rows
                            if row.get('real_nm_id') is not None and str(row.get('spend_source') or 'none') == 'none'
                        ]
                        if remaining_app_spend > 0:
                            scopes.append({
                                'scope_key': _historical_ads_scope_key(
                                    'app' if app_eligible else 'aggregate_without_nm',
                                    cid,
                                    d,
                                    current_app_type,
                                    app_index,
                                    None,
                                ),
                                'source': 'app' if app_eligible else 'aggregate_without_nm',
                                'campaign_id': str(cid or ''),
                                'date': d,
                                'app_type': str(current_app_type or '').strip() or None,
                                'source_spend': remaining_app_spend,
                            })
                            if app_eligible:
                                for row in simulated_app_rows:
                                    if row.get('real_nm_id') is not None and str(row.get('spend_source') or 'none') == 'none':
                                        row['spend_source'] = app_spend_source
                    simulated_day_rows.extend(simulated_app_rows)
                    continue

                app_article = app_node.get('supplierArticle') or app_node.get('article')
                app_nm_id = app_node.get('nmId') or app_node.get('nm') or app_node.get('id')
                real_app_nm_id = _historical_ads_real_nm_id(app_nm_id)
                if app_spend_source != 'none' or app_article not in (None, '') or app_nm_id not in (None, ''):
                    if app_spend_source != 'none':
                        scopes.append({
                            'scope_key': _historical_ads_scope_key(
                                'app' if real_app_nm_id is not None else 'aggregate_without_nm',
                                cid,
                                d,
                                current_app_type,
                                app_index,
                                None,
                            ),
                            'source': 'app' if real_app_nm_id is not None else 'aggregate_without_nm',
                            'campaign_id': str(cid or ''),
                            'date': d,
                            'app_type': str(current_app_type or '').strip() or None,
                            'source_spend': round(_num(app_spend), 2),
                        })
                    simulated_day_rows.append({
                        'real_nm_id': real_app_nm_id,
                        'spend_source': app_spend_source,
                        'app_type': current_app_type,
                        'app_index': app_index,
                    })

            if day_spend_source != 'none':
                simulated_spendful_day_total = round(sum(
                    _num(day_spend) if False else 0.0 for _ in []
                ), 2)
                simulated_spendful_day_total = 0.0
                for row in simulated_day_rows:
                    if str(row.get('spend_source') or 'none') != 'none':
                        # These rows already account for spend via direct/app scopes.
                        pass
                # Reconstruct the day-level remainder using raw source scopes already collected for this exact day.
                existing_day_source_total = round(sum(
                    _num(scope.get('source_spend'))
                    for scope in scopes
                    if str(scope.get('campaign_id') or '') == str(cid or '')
                    and str(scope.get('date') or '') == d
                ), 2)
                remaining_day_spend = round(max(0.0, _num(day_spend) - existing_day_source_total), 2)
                day_eligible = [row for row in simulated_day_rows if row.get('real_nm_id') is not None and str(row.get('spend_source') or 'none') == 'none']
                if remaining_day_spend > 0:
                    scopes.append({
                        'scope_key': _historical_ads_scope_key(
                            'day' if day_eligible else 'aggregate_without_nm',
                            cid,
                            d,
                            None,
                            -1,
                            None,
                        ),
                        'source': 'day' if day_eligible else 'aggregate_without_nm',
                        'campaign_id': str(cid or ''),
                        'date': d,
                        'app_type': None,
                        'source_spend': remaining_day_spend,
                    })
    return scopes


def _historical_ads_iterator_scope_for_row(row):
    source = _historical_ads_iterator_allocation_source(row)
    campaign_id = row.get('trace_campaign_id') or row.get('campaign_id')
    date_value = row.get('trace_date') or row.get('date')
    app_type = row.get('trace_app_type') or row.get('app_type')
    app_index = row.get('trace_app_index')
    item_index = row.get('trace_item_index')
    if source == 'direct_nm':
        return source, _historical_ads_scope_key(source, campaign_id, date_value, app_type, app_index, item_index)
    aggregate_key = str(row.get('aggregate_key') or '').strip()
    if source == 'app':
        return source, _historical_ads_scope_key(source, campaign_id, date_value, app_type, app_index, None)
    if source == 'day':
        return source, _historical_ads_scope_key(source, campaign_id, date_value, None, -1, None)
    if source == 'aggregate_without_nm':
        if aggregate_key.startswith(('agg_app:', 'agg_app_flat:', 'agg_app_remainder:')):
            return source, _historical_ads_scope_key(source, campaign_id, date_value, app_type, app_index, None)
        return source, _historical_ads_scope_key(source, campaign_id, date_value, None, -1, None)
    return source, _historical_ads_scope_key(source, campaign_id, date_value, app_type, app_index, item_index)


def _historical_ads_iterator_delta_diagnostics(payload, rows):
    expected_scopes = _historical_ads_expected_iterator_scopes(payload)
    scope_map = {}
    source_totals = {
        key: {'source': key, 'source_spend': 0.0, 'allocated_spend': 0.0, 'delta': 0.0}
        for key in ('direct_nm', 'app', 'day', 'aggregate_without_nm')
    }
    campaign_totals = {}

    for item in expected_scopes:
        key = item.get('scope_key')
        if key not in scope_map:
            scope_map[key] = {
                'scope_key': key,
                'source': item.get('source'),
                'campaign_id': item.get('campaign_id'),
                'date': item.get('date'),
                'app_type': item.get('app_type'),
                'source_spend': 0.0,
                'allocated_spend': 0.0,
                'delta': 0.0,
            }
        scope_map[key]['source_spend'] = round(scope_map[key]['source_spend'] + _num(item.get('source_spend')), 2)

    for row in rows or []:
        source, key = _historical_ads_iterator_scope_for_row(row)
        if key not in scope_map:
            scope_map[key] = {
                'scope_key': key,
                'source': source,
                'campaign_id': str(row.get('trace_campaign_id') or row.get('campaign_id') or ''),
                'date': str(row.get('trace_date') or row.get('date') or '')[:10],
                'app_type': str(row.get('trace_app_type') or row.get('app_type') or '').strip() or None,
                'source_spend': 0.0,
                'allocated_spend': 0.0,
                'delta': 0.0,
            }
        scope_map[key]['allocated_spend'] = round(scope_map[key]['allocated_spend'] + _num(row.get('spend')), 2)

    scopes = []
    for item in scope_map.values():
        item['delta'] = round(_num(item.get('allocated_spend')) - _num(item.get('source_spend')), 2)
        scopes.append(item)
        source = item.get('source')
        if source in source_totals:
            source_totals[source]['source_spend'] = round(source_totals[source]['source_spend'] + _num(item.get('source_spend')), 2)
            source_totals[source]['allocated_spend'] = round(source_totals[source]['allocated_spend'] + _num(item.get('allocated_spend')), 2)
        campaign_id = str(item.get('campaign_id') or '')
        if campaign_id:
            bucket = campaign_totals.setdefault(campaign_id, {
                'campaign_id': campaign_id,
                'source_spend': 0.0,
                'allocated_spend': 0.0,
                'delta': 0.0,
            })
            bucket['source_spend'] = round(bucket['source_spend'] + _num(item.get('source_spend')), 2)
            bucket['allocated_spend'] = round(bucket['allocated_spend'] + _num(item.get('allocated_spend')), 2)

    for item in source_totals.values():
        item['delta'] = round(_num(item.get('allocated_spend')) - _num(item.get('source_spend')), 2)
    for item in campaign_totals.values():
        item['delta'] = round(_num(item.get('allocated_spend')) - _num(item.get('source_spend')), 2)

    top_scope_deltas = sorted(
        scopes,
        key=lambda item: (abs(_num(item.get('delta'))), abs(_num(item.get('source_spend')))),
        reverse=True,
    )[:20]
    max_delta_campaigns = sorted(
        campaign_totals.values(),
        key=lambda item: (abs(_num(item.get('delta'))), abs(_num(item.get('source_spend')))),
        reverse=True,
    )[:20]

    total_source_spend = round(sum(_num(item.get('source_spend')) for item in scopes), 2)
    total_allocated_spend = round(sum(_num(item.get('allocated_spend')) for item in scopes), 2)
    total_delta = round(total_allocated_spend - total_source_spend, 2)
    return {
        'scope_deltas_top20': top_scope_deltas,
        'source_spend_breakdown': [source_totals[key] for key in ('direct_nm', 'app', 'day', 'aggregate_without_nm')],
        'max_delta_campaigns': max_delta_campaigns,
        'total_source_spend': total_source_spend,
        'total_allocated_spend': total_allocated_spend,
        'total_delta': total_delta,
    }


def _historical_ads_iterator_breakdown(cur, telegram_id, rows):
    source_order = ('direct_nm', 'app', 'day', 'aggregate_without_nm', 'unknown')
    method_order = ('direct', 'sum_price', 'orders', 'clicks', 'equal', 'none')
    source_buckets = {
        key: {
            'source': key,
            'rows_count': 0,
            'spend_sum': 0.0,
            'revenue_sum': 0.0,
            'unique_nm_ids': set(),
            'matched_sales_ids': set(),
            'matched_articles': set(),
            'linked_spend': 0.0,
        }
        for key in source_order
    }
    method_buckets = {
        key: {
            'method': key,
            'rows_count': 0,
            'spend_sum': 0.0,
        }
        for key in method_order
    }
    quality = {
        'rows_with_positive_nm_id': 0,
        'rows_with_null_nm_id': 0,
        'rows_with_negative_nm_id': 0,
        'spend_with_positive_nm_id': 0.0,
        'spend_with_null_nm_id': 0.0,
        'spend_with_negative_nm_id': 0.0,
    }
    total_spend = round(sum(_num(row.get('spend')) for row in (rows or [])), 2)

    for index, row in enumerate(rows or []):
        source = _historical_ads_iterator_allocation_source(row)
        if source not in source_buckets:
            source = 'unknown'
        method = _historical_ads_iterator_allocation_method(row)
        if method not in method_buckets:
            method = 'none'
        bucket = source_buckets[source]
        method_bucket = method_buckets[method]
        spend = round(_num(row.get('spend')), 2)
        revenue = round(_num(row.get('sum_price')), 2)
        nm_id = row.get('nm_id')
        real_nm_id = _historical_ads_real_nm_id(nm_id)
        article = str(row.get('article') or '').strip()
        matched_sales, matched_products = _advertising_match_flags(cur, telegram_id, nm_id, article)

        bucket['rows_count'] += 1
        bucket['spend_sum'] = round(bucket['spend_sum'] + spend, 2)
        bucket['revenue_sum'] = round(bucket['revenue_sum'] + revenue, 2)
        method_bucket['rows_count'] += 1
        method_bucket['spend_sum'] = round(method_bucket['spend_sum'] + spend, 2)

        if real_nm_id is not None:
            bucket['unique_nm_ids'].add(real_nm_id)
            quality['rows_with_positive_nm_id'] += 1
            quality['spend_with_positive_nm_id'] = round(quality['spend_with_positive_nm_id'] + spend, 2)
        else:
            try:
                normalized = int(str(nm_id).strip())
                if normalized < 0:
                    quality['rows_with_negative_nm_id'] += 1
                    quality['spend_with_negative_nm_id'] = round(quality['spend_with_negative_nm_id'] + spend, 2)
                else:
                    quality['rows_with_null_nm_id'] += 1
                    quality['spend_with_null_nm_id'] = round(quality['spend_with_null_nm_id'] + spend, 2)
            except Exception:
                quality['rows_with_null_nm_id'] += 1
                quality['spend_with_null_nm_id'] = round(quality['spend_with_null_nm_id'] + spend, 2)

        if matched_sales:
            bucket['matched_sales_ids'].add(real_nm_id if real_nm_id is not None else f'row:{index}')
            bucket['linked_spend'] = round(bucket['linked_spend'] + spend, 2)
        elif matched_products:
            bucket['linked_spend'] = round(bucket['linked_spend'] + spend, 2)
        if article and (matched_sales or matched_products):
            bucket['matched_articles'].add(article)

    allocation_breakdown = []
    for key in source_order:
        bucket = source_buckets[key]
        allocation_breakdown.append({
            'source': key,
            'rows_count': int(bucket['rows_count']),
            'spend_sum': round(bucket['spend_sum'], 2),
            'revenue_sum': round(bucket['revenue_sum'], 2),
            'unique_nm_id_count': int(len(bucket['unique_nm_ids'])),
            'matched_sales_count': int(len(bucket['matched_sales_ids'])),
            'matched_supplier_article_count': int(len(bucket['matched_articles'])),
            'linked_spend': round(bucket['linked_spend'], 2),
            'linkability_percent': round((bucket['linked_spend'] / bucket['spend_sum'] * 100) if bucket['spend_sum'] else 0, 1),
        })

    method_breakdown = []
    for key in method_order:
        bucket = method_buckets[key]
        method_breakdown.append({
            'method': key,
            'rows_count': int(bucket['rows_count']),
            'spend_sum': round(bucket['spend_sum'], 2),
            'share_of_total_spend_percent': round((bucket['spend_sum'] / total_spend * 100) if total_spend else 0, 1),
        })

    warnings = []
    aggregate_without_nm_spend = next((item['spend_sum'] for item in allocation_breakdown if item['source'] == 'aggregate_without_nm'), 0.0)
    equal_spend = next((item['spend_sum'] for item in method_breakdown if item['method'] == 'equal'), 0.0)
    positive_nm_spend_share = round((quality['spend_with_positive_nm_id'] / total_spend * 100) if total_spend else 0, 1)
    if total_spend > 0 and aggregate_without_nm_spend / total_spend > 0.10:
        warnings.append('too_much_unlinked_aggregate_spend')
    if total_spend > 0 and equal_spend / total_spend > 0.30:
        warnings.append('too_much_equal_allocation')
    if total_spend > 0 and positive_nm_spend_share < 80:
        warnings.append('low_real_nmid_coverage')

    return {
        'allocation_breakdown': allocation_breakdown,
        'allocation_method_breakdown': method_breakdown,
        'real_nmid_quality': quality,
        'linkability_by_source': [
            {
                'source': item['source'],
                'spend': item['spend_sum'],
                'linked_spend': item['linked_spend'],
                'linkability_percent': item['linkability_percent'],
            }
            for item in allocation_breakdown
        ],
        'warnings': warnings,
    }


def historical_advertising_audit(telegram_id, token, start_date, end_date, token_source='unknown'):
    init_db()
    snapshot = {
        'status': 'SUCCESS',
        'period_begin': str(start_date),
        'period_end': str(end_date),
        'campaigns_checked': [],
        'fullstats_status': None,
        'cooldown_active': False,
        'cooldown': None,
        'raw_fullstats': [],
        'iterator_check': {
            'rows_count': 0,
            'positive_nm_id': 0,
            'negative_nm_id': 0,
            'null_nm_id': 0,
            'source_spend': 0.0,
            'rows_spend': 0.0,
            'delta': 0.0,
            'warning': None,
            'sample_rows': [],
        },
        'iterator_delta_diagnostics': {
            'total_source_spend': 0.0,
            'total_allocated_spend': 0.0,
            'total_delta': 0.0,
            'source_spend_breakdown': [],
            'scope_deltas_top20': [],
            'max_delta_campaigns': [],
        },
        'prepare_rows_check': {
            'rows_count': 0,
            'positive_nm_id': 0,
            'negative_nm_id': 0,
            'null_nm_id': 0,
            'rows_with_supplier_article': 0,
            'rows_matching_sales_by_nm_id': 0,
            'source_spend': 0.0,
            'rows_spend': 0.0,
            'delta': 0.0,
            'warning': None,
            'sample_rows': [],
        },
        'historical_cache_check': {
            'rows_count': 0,
            'positive_nm_id': 0,
            'negative_nm_id': 0,
            'null_nm_id': 0,
            'rows_with_supplier_article': 0,
            'projected_linkability': 0.0,
            'source_spend': 0.0,
            'rows_spend': 0.0,
            'delta': 0.0,
            'warning': None,
            'sample_rows': [],
        },
        'saved_cache_file_check': {
            'exists': False,
            'is_valid': False,
            'created_at': None,
            'rows_count': 0,
            'positive_nm_id': 0,
            'negative_nm_id': 0,
            'null_nm_id': 0,
            'rows_with_supplier_article': 0,
            'projected_linkability': 0.0,
        },
        'current_db': _advertising_period_snapshot(telegram_id, start_date, end_date),
        'allocation_breakdown': [],
        'allocation_method_breakdown': [],
        'real_nmid_quality': {},
        'linkability_by_source': [],
        'warnings': [],
        'loss_point': 'unknown',
        'verdict': 'unknown',
        'recommendation': 'Нужна дополнительная диагностика historical advertising path.',
    }

    cooldown_row = get_api_cooldown(telegram_id, 'advertising') or {}
    if _cooldown_status(telegram_id, 'advertising'):
        snapshot['status'] = 'ADS_COOLDOWN_ACTIVE'
        snapshot['fullstats_status'] = 'ADS_COOLDOWN_ACTIVE'
        snapshot['cooldown_active'] = True
        snapshot['cooldown'] = {
            'retry_after': cooldown_row.get('retry_after'),
            'last_status': cooldown_row.get('last_status'),
            'updated_at': cooldown_row.get('updated_at'),
        }
        snapshot['loss_point'] = 'unknown'
        snapshot['verdict'] = 'unknown'
        snapshot['recommendation'] = 'ADS_COOLDOWN_ACTIVE'
        return snapshot

    conn = sqlite3.connect(DB_NAME)
    try:
        cur = conn.cursor()
        campaigns = _historical_ads_select_top_campaigns(cur, telegram_id, start_date, end_date, limit=3)
        snapshot['campaigns_checked'] = campaigns
        if not campaigns:
            snapshot['status'] = 'NO_LOCAL_CAMPAIGNS'
            snapshot['fullstats_status'] = 'NO_LOCAL_CAMPAIGNS'
            snapshot['recommendation'] = 'В local advertising нет campaign_id за выбранный период.'
            return snapshot

        batch_ids = []
        for item in campaigns:
            try:
                batch_ids.append(int(str(item.get('campaign_id')).strip()))
            except Exception:
                pass
        payload, fullstats_status = _fetch_fullstats_batch(
            token,
            batch_ids,
            str(start_date),
            str(end_date),
            timeout=60,
            token_source=token_source,
        )
        snapshot['fullstats_status'] = fullstats_status
        if str(fullstats_status).startswith('FULLSTATS_429_SAFE_COOLDOWN:'):
            snapshot['status'] = fullstats_status
            snapshot['recommendation'] = 'fullstats вернул 429, аудит остановлен без повторных запросов.'
            return snapshot
        if fullstats_status != 'SUCCESS' or payload is None:
            snapshot['status'] = fullstats_status or 'FULLSTATS_EMPTY'
            snapshot['recommendation'] = 'fullstats не вернул пригодный payload для historicalaudit.'
            return snapshot

        snapshot['raw_fullstats'] = _historical_ads_raw_summary(cur, telegram_id, campaigns, payload)
        source_total_spend = _fullstats_source_total_spend(payload)

        iterator_rows = list(_iter_fullstats_rows(payload, include_trace=True) or [])
        iterator_stats = _historical_ads_count_nm(iterator_rows, field='nm_id')
        iterator_rows_spend = round(sum(_num(row.get('spend')) for row in iterator_rows), 2)
        iterator_delta = round(iterator_rows_spend - source_total_spend, 2)
        iterator_breakdown = _historical_ads_iterator_breakdown(cur, telegram_id, iterator_rows)
        iterator_delta_diagnostics = _historical_ads_iterator_delta_diagnostics(payload, iterator_rows)
        snapshot['iterator_check'] = {
            **iterator_stats,
            'source_spend': source_total_spend,
            'rows_spend': iterator_rows_spend,
            'delta': iterator_delta,
            'warning': 'delta_gt_1_rub' if abs(iterator_delta) > 1 else None,
            'sample_rows': _historical_ads_prepare_sample(
                iterator_rows,
                ('campaign_id', 'date', 'app_type', 'nm_id', 'name', 'spend', 'sum_price'),
            ),
        }
        snapshot['allocation_breakdown'] = list(iterator_breakdown.get('allocation_breakdown') or [])
        snapshot['allocation_method_breakdown'] = list(iterator_breakdown.get('allocation_method_breakdown') or [])
        snapshot['real_nmid_quality'] = dict(iterator_breakdown.get('real_nmid_quality') or {})
        snapshot['linkability_by_source'] = list(iterator_breakdown.get('linkability_by_source') or [])
        snapshot['iterator_delta_diagnostics'] = dict(iterator_delta_diagnostics or {})
        snapshot['warnings'] = list(iterator_breakdown.get('warnings') or [])
        if abs(iterator_delta) > 1 and 'spend_delta_gt_1_rub' not in snapshot['warnings']:
            snapshot['warnings'].append('spend_delta_gt_1_rub')

        prepared = _prepare_advertising_rows(cur, telegram_id, payload)
        prepared_rows = [_advertising_tuple_to_dict(item) for item in prepared.get('parsed_rows') or []]
        prepared_stats = _historical_ads_count_nm(prepared_rows, field='nm_id')
        rows_with_supplier_article = 0
        rows_matching_sales_by_nm_id = 0
        for row in prepared_rows:
            article = str(row.get('supplier_article') or '').strip()
            if article:
                rows_with_supplier_article += 1
            nm_id = _historical_ads_real_nm_id(row.get('nm_id'))
            if nm_id is not None:
                cur.execute(
                    "SELECT 1 FROM sales WHERE telegram_id=? AND nm_id=? LIMIT 1",
                    (telegram_id, nm_id),
                )
                if cur.fetchone() is not None:
                    rows_matching_sales_by_nm_id += 1
        prepared_rows_spend = round(sum(_num(row.get('spend')) for row in prepared_rows), 2)
        prepared_delta = round(prepared_rows_spend - source_total_spend, 2)
        snapshot['prepare_rows_check'] = {
            **prepared_stats,
            'rows_with_supplier_article': int(rows_with_supplier_article),
            'rows_matching_sales_by_nm_id': int(rows_matching_sales_by_nm_id),
            'source_spend': source_total_spend,
            'rows_spend': prepared_rows_spend,
            'delta': prepared_delta,
            'warning': 'delta_gt_1_rub' if abs(prepared_delta) > 1 else None,
            'sample_rows': _historical_ads_prepare_sample(
                prepared_rows,
                ('unique_key', 'campaign_id', 'advert_date', 'nm_id', 'supplier_article', 'app_type', 'name', 'spend', 'sum_price'),
            ),
        }

        cache_rows = list(prepared_rows)
        cache_metrics = _advertising_projected_metrics(cur, telegram_id, cache_rows)
        cache_payload_info = _build_ads_historical_cache_payload(
            telegram_id,
            start_date,
            end_date,
            cache_rows,
            {
                'campaigns_found': int(len(batch_ids)),
                'advertising_rows': int(cache_metrics.get('rows_after_filter') or 0),
                'rows_with_real_nmid': int(cache_metrics.get('rows_with_real_nmid') or 0),
                'rows_with_placeholder_nmid': int(cache_metrics.get('rows_with_placeholder_nmid') or 0),
                'rows_matching_sales': int(cache_metrics.get('rows_matching_sales') or 0),
                'rows_matching_products': int(cache_metrics.get('rows_matching_products') or 0),
                'projected_linkability': round(float(cache_metrics.get('projected_linkability') or 0), 1),
                'projected_linked_spend': round(float(cache_metrics.get('projected_linked_spend') or 0), 2),
                'projected_linked_revenue': round(float(cache_metrics.get('projected_linked_revenue') or 0), 2),
                'total_spend': round(float(cache_metrics.get('total_spend') or 0), 2),
            },
        )
        cache_stats = dict(cache_payload_info.get('cache_debug') or {})
        cache_rows_spend = round(sum(_num(row.get('spend')) for row in cache_rows), 2)
        cache_delta = round(cache_rows_spend - source_total_spend, 2)
        snapshot['historical_cache_check'] = {
            **cache_stats,
            'projected_linkability': round(float(cache_metrics.get('projected_linkability') or 0), 1),
            'source_spend': source_total_spend,
            'rows_spend': cache_rows_spend,
            'delta': cache_delta,
            'warning': 'delta_gt_1_rub' if abs(cache_delta) > 1 else None,
            'sample_rows': _historical_ads_prepare_sample(
                cache_rows,
                ('unique_key', 'campaign_id', 'advert_date', 'nm_id', 'supplier_article', 'app_type', 'name', 'spend', 'sum_price'),
            ),
        }
        saved_cache = _read_ads_historical_cache(telegram_id, start_date, end_date)
        saved_cache_rows = list(saved_cache.get('rows') or [])
        saved_cache_meta = dict(saved_cache.get('metadata') or {})
        saved_cache_debug = _historical_ads_rows_debug(saved_cache_rows, field='nm_id')
        snapshot['saved_cache_file_check'] = {
            'exists': bool(saved_cache.get('exists')),
            'is_valid': bool(saved_cache.get('is_valid')),
            'path': saved_cache.get('path'),
            'file_size': int(saved_cache.get('file_size') or 0),
            'created_at': saved_cache_meta.get('created_at'),
            **saved_cache_debug,
            'projected_linkability': round(float(saved_cache_meta.get('cache_linkability') or saved_cache_meta.get('projected_linkability') or 0), 1),
        }

        raw_has_real = any((item.get('raw_real_nmid_count') or 0) > 0 for item in snapshot['raw_fullstats'])
        iterator_positive = int(snapshot['iterator_check'].get('positive_nm_id') or 0)
        prepared_positive = int(snapshot['prepare_rows_check'].get('positive_nm_id') or 0)
        cache_positive = int(snapshot['historical_cache_check'].get('positive_nm_id') or 0)
        current_positive = int((snapshot.get('current_db') or {}).get('rows_with_positive_nmid') or 0)
        current_negative = int((snapshot.get('current_db') or {}).get('rows_with_negative_nmid') or 0)

        if not raw_has_real:
            snapshot['loss_point'] = 'raw_missing_real_nmid'
            snapshot['verdict'] = 'unknown'
            snapshot['recommendation'] = 'Raw fullstats по выбранным campaign_id не содержит real nmID. Нужна дополнительная проверка payload.'
        elif iterator_positive <= 0:
            snapshot['loss_point'] = 'iterator_loses_nmid'
            snapshot['verdict'] = 'historical_uses_old_parser'
            snapshot['recommendation'] = 'Исправить _iter_fullstats_rows/_build_fullstats_row, чтобы брать nm_id из days[*].apps[*].nms[*].nmId.'
        elif prepared_positive <= 0:
            snapshot['loss_point'] = 'prepare_rows_loses_nmid'
            snapshot['verdict'] = 'prepare_rows_overwrites_nmid'
            snapshot['recommendation'] = 'Исправить _prepare_advertising_rows, чтобы не заменять real nm_id на placeholder/null.'
        elif cache_positive <= 0:
            snapshot['loss_point'] = 'historical_cache_loses_nmid'
            snapshot['verdict'] = 'cache_builder_overwrites_nmid'
            snapshot['recommendation'] = 'Исправить historical_advertising_backfill cache builder — он использует старые строки.'
        elif current_positive <= 0 and current_negative > 0:
            snapshot['loss_point'] = 'local_existing_db_old_only'
            snapshot['verdict'] = 'ready_for_ads_historical_reload'
            snapshot['recommendation'] = 'Можно запускать /ads applyhistorical.'
        else:
            snapshot['loss_point'] = 'unknown'
            snapshot['verdict'] = 'ready_for_ads_historical_reload'
            snapshot['recommendation'] = 'Можно запускать /ads applyhistorical.'
    finally:
        conn.close()
    return snapshot


def apply_historical_advertising_backfill(telegram_id, token, start_date, end_date):
    init_db()
    db_before = _advertising_period_snapshot(telegram_id, start_date, end_date)
    cache = _read_ads_historical_cache(telegram_id, start_date, end_date)
    metadata = cache.get('metadata') or {}
    rows = list(cache.get('rows') or [])
    result = {
        'status': 'SUCCESS',
        'start_date': str(start_date),
        'end_date': str(end_date),
        'cache_used': 'no',
        'cache_created_at': metadata.get('created_at'),
        'cache_path': cache.get('path'),
        'summary': {
            'campaigns_found': int(metadata.get('campaigns_found') or 0),
            'advertising_rows': int(metadata.get('advertising_rows') or 0),
            'rows_with_real_nmid': int(metadata.get('cache_positive_nm_id') or metadata.get('rows_with_real_nmid') or 0),
            'rows_with_placeholder_nmid': int(metadata.get('rows_with_placeholder_nmid') or 0),
            'rows_matching_sales': int(metadata.get('rows_matching_sales') or 0),
            'rows_matching_products': int(metadata.get('rows_matching_products') or 0),
            'projected_linkability': round(float(metadata.get('cache_linkability') or metadata.get('projected_linkability') or 0), 1),
            'projected_linked_spend': round(float(metadata.get('projected_linked_spend') or 0), 2),
            'projected_linked_revenue': round(float(metadata.get('projected_linked_revenue') or 0), 2),
            'total_spend': round(float(metadata.get('total_spend') or 0), 2),
        },
        'db_before': db_before,
        'apply': {'inserted': 0, 'updated': 0, 'skipped': 0, 'invalid': 0, 'errors': 0},
        'db_after': db_before,
        'guards': {
            'status_success': False,
            'rows_after_filter_positive': False,
            'rows_with_real_nmid_positive': False,
            'projected_linkability_improves': False,
        },
        'guard_failures': [],
        'write_performed': False,
    }
    if not cache.get('is_valid'):
        result['status'] = 'CACHE_MISSING_OR_EXPIRED'
        return result
    result['cache_used'] = 'yes'
    result['guards'] = {
        'status_success': True,
        'rows_after_filter_positive': int(result['summary'].get('advertising_rows') or 0) > 0,
        'rows_with_real_nmid_positive': int(result['summary'].get('rows_with_real_nmid') or 0) > 0,
        'projected_linkability_improves': float(result['summary'].get('projected_linkability') or 0) > float(db_before.get('linkability') or 0),
    }
    if not result['guards']['status_success']:
        result['guard_failures'].append('status != SUCCESS')
    if not result['guards']['rows_after_filter_positive']:
        result['guard_failures'].append('rows_after_filter <= 0')
    if not result['guards']['rows_with_real_nmid_positive']:
        result['guard_failures'].append('rows_with_real_nmID <= 0')
    if not result['guards']['projected_linkability_improves']:
        result['guard_failures'].append('projected_linkability <= current_linkability')
    if result['guard_failures']:
        result['status'] = 'GUARD_BLOCKED'
        return result
    conn = sqlite3.connect(DB_NAME)
    try:
        cur = conn.cursor()
        stats = _safe_upsert_historical_advertising_rows(cur, telegram_id, rows, start_date, end_date)
        conn.commit()
        result['apply'] = {
            'inserted': int(stats.get('inserted') or 0),
            'updated': int(stats.get('updated') or 0),
            'skipped': int(stats.get('skipped') or 0),
            'invalid': int(stats.get('invalid') or 0),
            'errors': int(stats.get('errors') or 0),
        }
        result['db_after'] = _advertising_period_snapshot(telegram_id, start_date, end_date)
        result['write_performed'] = True
    except Exception:
        conn.rollback()
        result['status'] = 'EXCEPTION'
        result['apply']['errors'] = 1
    finally:
        conn.close()
    return result


def _safe_call(fn, *args, **kwargs):
    caller = kwargs.pop('cooldown_caller', None) or getattr(fn, '__name__', 'unknown')
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        return 0, f'EXCEPTION:{type(e).__name__}'


def _build_update_status(blocks):
    bad = {name: data for name, data in blocks.items() if data['status'] != 'SUCCESS'}
    if len(bad) == len(blocks):
        overall = 'ERROR'
    elif bad:
        overall = 'PARTIAL_SUCCESS'
    else:
        overall = 'SUCCESS'
    return {'overall': overall, 'blocks': blocks}


def format_update_status(status):
    if not isinstance(status, dict):
        return str(status)
    parts = [status.get('overall', 'UNKNOWN')]
    for name, data in status.get('blocks', {}).items():
        parts.append(f"{name}:{data.get('status', 'UNKNOWN')}:{int(data.get('loaded', 0) or 0)}")
    return '|'.join(parts)


def _now_dt():
    return datetime.now()


def _now_str():
    return _now_dt().strftime('%Y-%m-%d %H:%M:%S')


def _parse_dt(value):
    if not value:
        return None
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(str(value), fmt)
        except Exception:
            pass
    return None


def get_api_cooldown(telegram_id, api_block):
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT retry_after,last_status,updated_at FROM api_cooldowns WHERE telegram_id=? AND api_block=?', (telegram_id, api_block))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {'retry_after': row[0], 'last_status': row[1], 'updated_at': row[2]}


def set_api_cooldown(telegram_id, api_block, status, retry_seconds=None, caller='unknown'):
    init_db()
    now_dt = _now_dt()
    retry_after = (now_dt + timedelta(seconds=max(0, int(float(retry_seconds or 0))))).strftime('%Y-%m-%d %H:%M:%S') if retry_seconds is not None else None
    _remember_cooldown_write(telegram_id, api_block, caller, status, retry_seconds, retry_after)
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
    INSERT INTO api_cooldowns(telegram_id,api_block,retry_after,last_status,updated_at)
    VALUES(?,?,?,?,?)
    ON CONFLICT(telegram_id,api_block) DO UPDATE SET
        retry_after=excluded.retry_after,
        last_status=excluded.last_status,
        updated_at=excluded.updated_at
    ''', (telegram_id, api_block, retry_after, status, _now_str()))
    conn.commit()
    conn.close()
    if api_block == 'advertising':
        _log_ads_cooldown_write(
            caller=caller,
            status=status,
            retry_after=retry_seconds,
            saved_until=retry_after,
        )
        _log_ads_cooldown_debug(
            status=status,
            retry_after=retry_seconds,
            saved_until=retry_after,
            now=now_dt.strftime('%Y-%m-%d %H:%M:%S'),
            remaining=max(0, int(float(retry_seconds or 0))) if retry_seconds is not None else None,
        )


def clear_api_cooldown(telegram_id, api_block, status='SUCCESS', caller='clear_api_cooldown'):
    set_api_cooldown(telegram_id, api_block, status, None, caller=caller)


def delete_api_cooldown(telegram_id, api_block):
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('DELETE FROM api_cooldowns WHERE telegram_id=? AND api_block=?', (telegram_id, api_block))
    deleted = int(cur.rowcount or 0)
    conn.commit()
    conn.close()
    return deleted


def _cooldown_status(telegram_id, api_block):
    row = get_api_cooldown(telegram_id, api_block)
    if not row:
        return None
    retry_after = _parse_dt(row.get('retry_after'))
    now_dt = _now_dt()
    if retry_after and retry_after > now_dt:
        seconds_left = int((retry_after - now_dt).total_seconds())
        if api_block == 'advertising':
            _log_ads_cooldown_debug(
                status=f'ADS_COOLDOWN:{seconds_left}',
                retry_after=row.get('retry_after'),
                saved_until=row.get('retry_after'),
                now=now_dt.strftime('%Y-%m-%d %H:%M:%S'),
                remaining=seconds_left,
            )
            return f'ADS_COOLDOWN:{seconds_left}'
        return f'SKIPPED_COOLDOWN:{seconds_left}'
    if api_block == 'advertising':
        _log_ads_cooldown_debug(
            status=row.get('last_status'),
            retry_after=row.get('retry_after'),
            saved_until=row.get('retry_after'),
            now=now_dt.strftime('%Y-%m-%d %H:%M:%S'),
            remaining=0 if retry_after else None,
        )
    return None


def _remember_status(telegram_id, api_block, status, caller='unknown'):
    status_str = str(status)
    if api_block == 'advertising':
        details = _get_last_ads_run_details(telegram_id)
        step_seconds = details.get('next_safe_seconds')
        real_fullstats_request = (
            step_seconds is not None
            or bool(details.get('api_cooldown_status'))
            or (
                details.get('campaign_id') is not None
                and bool(details.get('date'))
                and str(details.get('status') or '') in ('ADS_PARTIAL_PROGRESS', 'SUCCESS', 'FULLSTATS_INVALID_BEGIN')
            )
        )
        if status_str in ('ADS_PARTIAL_PROGRESS', 'SUCCESS', 'FULLSTATS_INVALID_BEGIN') and real_fullstats_request:
            try:
                seconds = int(float(step_seconds or ADS_SAFE_MIN_COOLDOWN_SECONDS))
            except Exception:
                seconds = ADS_SAFE_MIN_COOLDOWN_SECONDS
            set_api_cooldown(telegram_id, api_block, status, seconds, caller=caller)
            return
    if status_str.startswith('RATE_LIMIT:'):
        retry = status_str.split(':', 1)[1]
        try:
            seconds = int(float(retry))
        except Exception:
            seconds = 60
        set_api_cooldown(telegram_id, api_block, status, seconds, caller=caller)
    elif status_str.startswith('FULLSTATS_429:'):
        retry = status_str.split(':', 1)[1]
        try:
            seconds = int(float(retry))
        except Exception:
            seconds = 60
        set_api_cooldown(telegram_id, api_block, status, seconds, caller=caller)
    elif status_str.startswith('FULLSTATS_429_SAFE_COOLDOWN:'):
        retry = status_str.split(':', 1)[1]
        try:
            seconds = int(float(retry))
        except Exception:
            seconds = ADS_SAFE_MIN_COOLDOWN_SECONDS
        set_api_cooldown(telegram_id, api_block, status, seconds, caller=caller)
    elif status_str.startswith('ADS_STEP_COOLDOWN:'):
        retry = status_str.split(':', 1)[1]
        try:
            seconds = int(float(retry))
        except Exception:
            seconds = ADS_SAFE_MIN_COOLDOWN_SECONDS
        set_api_cooldown(telegram_id, api_block, status, seconds, caller=caller)
    elif status == 'SUCCESS':
        clear_api_cooldown(telegram_id, api_block, status, caller=f'{caller}->clear_api_cooldown')
    else:
        set_api_cooldown(telegram_id, api_block, status, None, caller=caller)


def _run_block(telegram_id, api_block, fn, *args, **kwargs):
    cooldown = _cooldown_status(telegram_id, api_block)
    if cooldown:
        return 0, cooldown
    loaded, status = _safe_call(fn, *args, **kwargs)
    caller = kwargs.get('cooldown_caller') or getattr(fn, '__name__', 'unknown')
    if api_block == 'advertising':
        details = _get_last_ads_run_details(telegram_id)
        cooldown_status = details.get('api_cooldown_status')
        if cooldown_status:
            _remember_status(telegram_id, api_block, cooldown_status, caller=caller)
        else:
            _remember_status(telegram_id, api_block, status, caller=caller)
    else:
        _remember_status(telegram_id, api_block, status, caller=caller)
    return loaded, status


def _article_by_nm(cur, telegram_id, nm_id):
    if not nm_id:
        return None
    cur.execute('''
    SELECT supplier_article
    FROM sales
    WHERE telegram_id=? AND nm_id=? AND supplier_article IS NOT NULL
    LIMIT 1
    ''', (telegram_id, nm_id))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute('''
    SELECT supplier_article
    FROM orders
    WHERE telegram_id=? AND nm_id=? AND supplier_article IS NOT NULL
    LIMIT 1
    ''', (telegram_id, nm_id))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute('''
    SELECT supplier_article
    FROM products
    WHERE telegram_id IN (?,0) AND supplier_article IS NOT NULL AND supplier_article!=''
    ORDER BY telegram_id DESC, last_price DESC, supplier_article
    ''', (telegram_id,))
    rows = [r[0] for r in cur.fetchall()]
    return rows[0] if len(rows) == 1 else None


def load_sales(telegram_id, token, days=30):
    start_date = _date_from(days)
    end_date = _today()
    audit = inspect_sales_api(token, start_date, end_date, telegram_id)
    if audit.get('status') != 'SUCCESS':
        return 0, audit.get('status')
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        stats = _persist_sales_rows(cur, telegram_id, audit.get('filtered_rows') or [])
        cur.execute('''
        INSERT OR IGNORE INTO products (telegram_id, supplier_article, cost_price, last_price)
        SELECT ?, supplier_article, 0, MAX(price_with_disc)
        FROM sales
        WHERE telegram_id=? AND supplier_article IS NOT NULL
        GROUP BY supplier_article
        ''', (telegram_id, telegram_id))
        conn.commit()
    finally:
        conn.close()
    saved = int(stats.get('inserted', 0)) + int(stats.get('updated', 0))
    logger.info(
        'LOAD SALES user=%s dateFrom=%s received=%s in_range=%s inserted=%s updated=%s skipped=%s invalid=%s',
        telegram_id,
        start_date,
        audit.get('received_rows'),
        audit.get('rows_in_range'),
        stats.get('inserted'),
        stats.get('updated'),
        stats.get('skipped'),
        stats.get('invalid'),
    )
    return saved, 'SUCCESS'


def load_orders(telegram_id, token, days=30):
    start_date = _date_from(days)
    end_date = _today()
    audit = inspect_orders_api(token, start_date, end_date, telegram_id)
    if audit.get('status') != 'SUCCESS':
        return 0, audit.get('status')
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        stats = _persist_orders_rows(cur, telegram_id, audit.get('filtered_rows') or [])
        conn.commit()
    finally:
        conn.close()
    saved = int(stats.get('inserted', 0)) + int(stats.get('updated', 0))
    logger.info(
        'LOAD ORDERS user=%s dateFrom=%s received=%s in_range=%s inserted=%s updated=%s skipped=%s invalid=%s',
        telegram_id,
        start_date,
        audit.get('received_rows'),
        audit.get('rows_in_range'),
        stats.get('inserted'),
        stats.get('updated'),
        stats.get('skipped'),
        stats.get('invalid'),
    )
    return saved, 'SUCCESS'


def load_stocks(telegram_id, token):
    data, status = _get(f'{STAT_API}/api/v1/supplier/stocks', token, {'dateFrom': '2019-01-01'}, timeout=90)
    if status != 'SUCCESS':
        return 0, status
    if not isinstance(data, list):
        return 0, 'INVALID_RESPONSE'

    today = _today()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('DELETE FROM stocks WHERE telegram_id=? AND stock_date=?', (telegram_id, today))
    saved = 0
    for x in data:
        if not isinstance(x, dict):
            continue
        article = x.get('supplierArticle')
        wh = x.get('warehouseName') or ''
        key = f'{telegram_id}:{today}:{article}:{wh}:{x.get("barcode")}'
        cur.execute('''
        INSERT OR REPLACE INTO stocks (
            unique_key, telegram_id, stock_date, supplier_article, nm_id, barcode,
            warehouse_name, quantity, quantity_full, in_way_to_client, in_way_from_client
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            key, telegram_id, today, article, x.get('nmId'), x.get('barcode'), wh,
            _int(x.get('quantity')), _int(x.get('quantityFull') or x.get('quantity')),
            _int(x.get('inWayToClient')), _int(x.get('inWayFromClient'))
        ))
        saved += 1
    conn.commit()
    conn.close()
    return saved, 'SUCCESS'


def _expense_insert(cur, key, telegram_id, date, etype, amount, article, comment, source):
    if amount <= 0:
        return 0
    cur.execute('''
    INSERT OR REPLACE INTO expenses (
        unique_key, telegram_id, expense_date, expense_type, amount,
        supplier_article, comment, source, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (key, telegram_id, date, etype, float(amount), article, comment, source, _dt()))
    return 1


def load_finance_expenses(telegram_id, token, days=30):
    date_from = _date_from(days)
    date_to = _today()
    rrdid = 0
    saved = 0
    page = 0
    parsed_rows = []
    raw_audit_rows = []

    # обновляем только API-затраты за период, ручные расходы не трогаем
    while True:
        page += 1
        data, status = _get(
            f'{STAT_API}/api/v5/supplier/reportDetailByPeriod',
            token,
            {'dateFrom': date_from, 'dateTo': date_to, 'limit': 100000, 'rrdid': rrdid},
            timeout=20,
            caller='load_finance_expenses->reportDetailByPeriod'
        )
        if status != 'SUCCESS':
            return saved, status
        if not isinstance(data, list):
            return saved, 'INVALID_RESPONSE'
        if not data:
            break

        for idx, row in enumerate(data):
            if not isinstance(row, dict):
                continue
            d = str(_first(row, ['sale_dt', 'rr_dt', 'date', 'operation_dt'], date_to))[:10]
            article = _first(row, ['sa_name', 'supplierArticle', 'supplier_article', 'supplierArticleName'])
            nm_id = _first(row, ['nm_id', 'nmID', 'nmId'])
            supplier_article = _first(row, ['supplier_article', 'supplierArticle', 'sa_name', 'saName']) or article
            srid = _first(row, ['srid', 'srId'])
            doc_type_name = _first(row, ['doc_type_name', 'docTypeName', 'doc_type'])
            operation_type = _first(row, ['operation_type', 'operationType'])
            payment_type = _first(row, ['payment_type', 'paymentType'])
            subject_name = _first(row, ['subject_name', 'subjectName'])
            brand_name = _first(row, ['brand_name', 'brandName'])
            sa_name = _first(row, ['sa_name', 'saName'])
            bonus_type_name = _first(row, ['bonus_type_name', 'bonusTypeName'])
            sticker_id = _first(row, ['sticker_id', 'stickerId'])
            gi_id = _first(row, ['gi_id', 'giId'])
            row_rrd = _first(row, ['rrd_id', 'rrdId', 'rrdid'], f'{page}:{idx}')
            penalty = _num(row.get('penalty'))
            deduction = _num(row.get('deduction'))
            acceptance = _num(row.get('acceptance'))
            acceptance_fee = _num(row.get('acceptance_fee')) + _num(row.get('acceptanceFee'))
            additional_payment = _num(row.get('additional_payment')) + _num(row.get('additionalPayment'))
            acquiring_fee = _num(row.get('acquiring_fee')) + _num(row.get('acquiringFee'))

            logistics = sum(abs(_num(row.get(x))) for x in [
                'delivery_rub', 'deliveryRub', 'return_amount', 'returnAmount',
                'rebill_logistic_cost', 'rebillLogisticCost', 'delivery_amount', 'deliveryAmount'
            ])
            storage = sum(abs(_num(row.get(x))) for x in [
                'storage_fee', 'storageFee', 'storage', 'storage_cost', 'storageCost'
            ])
            other = sum(abs(v) for v in [
                penalty, deduction, acceptance, acceptance_fee, additional_payment, acquiring_fee
            ])
            raw_audit_rows.append((
                telegram_id,
                str(row_rrd),
                d,
                float(penalty),
                float(deduction),
                float(acceptance),
                float(acceptance_fee),
                float(additional_payment),
                float(acquiring_fee),
                None if nm_id in (None, '') else str(nm_id),
                None if supplier_article in (None, '') else str(supplier_article),
                None if srid in (None, '') else str(srid),
                None if doc_type_name in (None, '') else str(doc_type_name),
                None if operation_type in (None, '') else str(operation_type),
                None if payment_type in (None, '') else str(payment_type),
                None if subject_name in (None, '') else str(subject_name),
                None if brand_name in (None, '') else str(brand_name),
                None if sa_name in (None, '') else str(sa_name),
                None if bonus_type_name in (None, '') else str(bonus_type_name),
                None if sticker_id in (None, '') else str(sticker_id),
                None if gi_id in (None, '') else str(gi_id),
                json.dumps(row, ensure_ascii=False, default=str),
                _dt(),
            ))
            parsed_rows.extend([
                (f'finance:{telegram_id}:{row_rrd}:logistics', telegram_id, d, 'logistics', logistics, article, 'WB finance logistics', 'api_finance'),
                (f'finance:{telegram_id}:{row_rrd}:storage', telegram_id, d, 'storage', storage, article, 'WB finance storage', 'api_finance'),
                (f'finance:{telegram_id}:{row_rrd}:other', telegram_id, d, 'other', other, article, 'WB finance other', 'api_finance'),
            ])

            next_rrd = _first(row, ['rrd_id', 'rrdId', 'rrdid'])
            if next_rrd:
                try:
                    rrdid = int(next_rrd)
                except Exception:
                    pass

        if len(data) < 100000 or page >= 10:
            break

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
    DELETE FROM expenses
    WHERE telegram_id=?
      AND source='api_finance'
      AND substr(expense_date,1,10)>=?
    ''', (telegram_id, date_from))
    cur.execute('''
    DELETE FROM finance_raw_audit
    WHERE telegram_id=?
      AND substr(report_date,1,10)>=?
    ''', (telegram_id, date_from))
    for key, tid, d, etype, amount, article, comment, source in parsed_rows:
        saved += _expense_insert(cur, key, tid, d, etype, amount, article, comment, source)
    cur.executemany('''
    INSERT INTO finance_raw_audit(
        telegram_id, rrd_id, report_date, penalty, deduction, acceptance,
        acceptance_fee, additional_payment, acquiring_fee, nm_id, supplier_article,
        srid, doc_type_name, operation_type, payment_type, subject_name, brand_name,
        sa_name, bonus_type_name, sticker_id, gi_id, raw_json, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', raw_audit_rows)
    conn.commit()
    conn.close()
    return saved, 'SUCCESS'


def get_finance_breakdown(token, days=30):
    date_from, date_to = _normalize_period_dates(days)
    rrdid = 0
    page = 0
    rows = []
    fields = [
        'penalty', 'deduction', 'acceptance', 'acceptance_fee', 'acceptanceFee',
        'additional_payment', 'additionalPayment', 'acquiring_fee', 'acquiringFee'
    ]

    while True:
        page += 1
        data, status = _get(
            f'{STAT_API}/api/v5/supplier/reportDetailByPeriod',
            token,
            {'dateFrom': date_from, 'dateTo': date_to, 'limit': 100000, 'rrdid': rrdid},
            timeout=20,
            caller='get_finance_breakdown->reportDetailByPeriod'
        )
        if status != 'SUCCESS':
            return {'status': status, 'categories': {}, 'fields': {}, 'total_other_abs': 0.0, 'rows': 0}
        if not isinstance(data, list):
            return {'status': 'INVALID_RESPONSE', 'categories': {}, 'fields': {}, 'total_other_abs': 0.0, 'rows': 0}
        if not data:
            break

        rows.extend([row for row in data if isinstance(row, dict)])
        next_rrd = _first(data[-1], ['rrd_id', 'rrdId', 'rrdid'])
        if next_rrd:
            try:
                rrdid = int(next_rrd)
            except Exception:
                pass
        if len(data) < 100000 or page >= 10:
            break

    field_stats = {}
    for field in fields:
        values = []
        for row in rows:
            value = row.get(field)
            if value in (None, '', 0, 0.0, '0', '0.0'):
                continue
            num = _num(value)
            if num == 0:
                continue
            values.append(num)
        if not values:
            continue
        field_stats[field] = {
            'sum_raw': round(sum(values), 2),
            'sum_abs': round(sum(abs(v) for v in values), 2),
            'positive_count': sum(1 for v in values if v > 0),
            'negative_count': sum(1 for v in values if v < 0),
            'nonzero_count': len(values),
            'average_sign': 'mixed' if any(v > 0 for v in values) and any(v < 0 for v in values) else ('positive' if all(v > 0 for v in values) else 'negative'),
        }

    categories = {
        'Штрафы': round(field_stats.get('penalty', {}).get('sum_abs', 0.0), 2),
        'Удержания': round(field_stats.get('deduction', {}).get('sum_abs', 0.0), 2),
        'Приёмка': round(
            field_stats.get('acceptance', {}).get('sum_abs', 0.0) +
            field_stats.get('acceptance_fee', {}).get('sum_abs', 0.0) +
            field_stats.get('acceptanceFee', {}).get('sum_abs', 0.0), 2
        ),
        'Доп. начисления': round(
            field_stats.get('additional_payment', {}).get('sum_abs', 0.0) +
            field_stats.get('additionalPayment', {}).get('sum_abs', 0.0), 2
        ),
        'Эквайринг': round(
            field_stats.get('acquiring_fee', {}).get('sum_abs', 0.0) +
            field_stats.get('acquiringFee', {}).get('sum_abs', 0.0), 2
        ),
    }
    categories = {k: v for k, v in categories.items() if v > 0}
    return {
        'status': 'SUCCESS',
        'categories': categories,
        'fields': field_stats,
        'total_other_abs': round(sum(categories.values()), 2),
        'rows': len(rows),
    }


def get_finance_audit(token, days=30, top_n=20):
    date_from, date_to = _normalize_period_dates(days)
    rrdid = 0
    page = 0
    rows = []
    fields = [
        'penalty', 'deduction', 'acceptance', 'acceptance_fee', 'acceptanceFee',
        'additional_payment', 'additionalPayment', 'acquiring_fee', 'acquiringFee'
    ]
    category_map = {
        'penalty': 'Штрафы',
        'deduction': 'Удержания',
        'acceptance': 'Приёмка',
        'acceptance_fee': 'Приёмка',
        'acceptanceFee': 'Приёмка',
        'additional_payment': 'Доп. начисления',
        'additionalPayment': 'Доп. начисления',
        'acquiring_fee': 'Эквайринг',
        'acquiringFee': 'Эквайринг',
    }

    while True:
        page += 1
        data, status = _get(
            f'{STAT_API}/api/v5/supplier/reportDetailByPeriod',
            token,
            {'dateFrom': date_from, 'dateTo': date_to, 'limit': 100000, 'rrdid': rrdid},
            timeout=20,
            caller='get_finance_audit->reportDetailByPeriod'
        )
        if status != 'SUCCESS':
            return {
                'status': status,
                'rows': 0,
                'fields': {},
                'categories': {},
                'top_entries': [],
                'positive_as_expense': [],
                'total_other_abs': 0.0,
            }
        if not isinstance(data, list):
            return {
                'status': 'INVALID_RESPONSE',
                'rows': 0,
                'fields': {},
                'categories': {},
                'top_entries': [],
                'positive_as_expense': [],
                'total_other_abs': 0.0,
            }
        if not data:
            break

        rows.extend([row for row in data if isinstance(row, dict)])
        next_rrd = _first(data[-1], ['rrd_id', 'rrdId', 'rrdid'])
        if next_rrd:
            try:
                rrdid = int(next_rrd)
            except Exception:
                pass
        if len(data) < 100000 or page >= 10:
            break

    field_stats = {}
    categories = {}
    top_entries = []
    positive_as_expense = []
    total_other_abs = 0.0

    for row in rows:
        row_date = str(_first(row, ['sale_dt', 'rr_dt', 'date', 'operation_dt'], date_to))[:10]
        article = _first(row, ['sa_name', 'supplierArticle', 'supplier_article', 'supplierArticleName'])
        for field in fields:
            raw_value = _num(row.get(field))
            if raw_value == 0:
                continue
            stored_value = abs(raw_value)
            sign = '+' if raw_value > 0 else '-'
            category = category_map.get(field, 'Прочее')
            total_other_abs += stored_value
            categories[category] = round(categories.get(category, 0.0) + stored_value, 2)
            field_stat = field_stats.setdefault(field, {
                'sum_raw': 0.0,
                'sum_abs': 0.0,
                'positive_count': 0,
                'negative_count': 0,
                'examples': [],
            })
            field_stat['sum_raw'] += raw_value
            field_stat['sum_abs'] += stored_value
            if raw_value > 0:
                field_stat['positive_count'] += 1
            else:
                field_stat['negative_count'] += 1
            if len(field_stat['examples']) < 5:
                field_stat['examples'].append({
                    'date': row_date,
                    'supplier_article': article,
                    'raw_value': round(raw_value, 2),
                    'stored_value': round(stored_value, 2),
                    'sign': sign,
                })
            entry = {
                'date': row_date,
                'amount': round(stored_value, 2),
                'category': category,
                'wb_field': field,
                'raw_value': round(raw_value, 2),
                'sign': sign,
                'stored_value': round(stored_value, 2),
                'supplier_article': article,
                'comment': 'WB finance other',
            }
            top_entries.append(entry)
            if raw_value > 0:
                positive_as_expense.append(entry)

    for stat in field_stats.values():
        stat['sum_raw'] = round(stat['sum_raw'], 2)
        stat['sum_abs'] = round(stat['sum_abs'], 2)
        stat['nonzero_count'] = int(stat['positive_count'] + stat['negative_count'])
        if stat['positive_count'] and stat['negative_count']:
            stat['average_sign'] = 'mixed'
        elif stat['positive_count']:
            stat['average_sign'] = 'positive'
        else:
            stat['average_sign'] = 'negative'

    top_entries.sort(key=lambda item: item['amount'], reverse=True)
    positive_as_expense.sort(key=lambda item: item['amount'], reverse=True)
    categories = {k: v for k, v in sorted(categories.items(), key=lambda item: item[1], reverse=True)}
    operations = []
    for field_name, stat in sorted(field_stats.items(), key=lambda item: abs(float(item[1].get('sum_raw') or 0)), reverse=True):
        avg_sign = str(stat.get('average_sign') or '')
        if avg_sign == 'positive':
            sign_label = 'начисление'
        elif avg_sign == 'negative':
            sign_label = 'расход'
        else:
            sign_label = 'смешанный'
        operations.append({
            'name': field_name,
            'sum_raw': round(float(stat.get('sum_raw') or 0), 2),
            'sum_abs': round(float(stat.get('sum_abs') or 0), 2),
            'rows_count': int(stat.get('nonzero_count') or 0),
            'sign': sign_label,
        })
    return {
        'status': 'SUCCESS',
        'rows': len(rows),
        'fields': field_stats,
        'categories': categories,
        'operations': operations,
        'top_entries': top_entries[:top_n],
        'positive_as_expense': positive_as_expense[:top_n],
        'total_other_abs': round(total_other_abs, 2),
    }


def get_finance_rawdeduction(token, days=30, limit=10):
    date_from, date_to = _normalize_period_dates(days)
    rrdid = 0
    page = 0
    rows = []
    money_fields = [
        'retail_amount',
        'ppvz_for_pay',
        'delivery_rub',
        'penalty',
        'additional_payment',
        'deduction',
        'amount',
        'sum',
        'total',
    ]
    descriptor_fields = [
        'operation_type',
        'operationType',
        'operation_name',
        'operationName',
        'category',
        'category_name',
        'categoryName',
        'doc_type_name',
        'docTypeName',
        'doc_type',
        'supplier_oper_name',
        'supplierOperName',
        'type',
    ]

    while True:
        page += 1
        data, status = _get(
            f'{STAT_API}/api/v5/supplier/reportDetailByPeriod',
            token,
            {'dateFrom': date_from, 'dateTo': date_to, 'limit': 100000, 'rrdid': rrdid},
            timeout=20,
            caller='get_finance_rawdeduction->reportDetailByPeriod'
        )
        if status != 'SUCCESS':
            return {'status': status, 'rows_count': 0, 'items': [], 'raw_sum': 0.0, 'expense_sum': 0.0, 'income_sum': 0.0}
        if not isinstance(data, list):
            return {'status': 'INVALID_RESPONSE', 'rows_count': 0, 'items': [], 'raw_sum': 0.0, 'expense_sum': 0.0, 'income_sum': 0.0}
        if not data:
            break
        rows.extend([row for row in data if isinstance(row, dict)])
        next_rrd = _first(data[-1], ['rrd_id', 'rrdId', 'rrdid'])
        if next_rrd:
            try:
                rrdid = int(next_rrd)
            except Exception:
                pass
        if len(data) < 100000 or page >= 10:
            break

    matched = []
    raw_sum = 0.0
    expense_sum = 0.0
    income_sum = 0.0
    for row in rows:
        descriptor_values = []
        matched_descriptor_pairs = []
        for field_name in descriptor_fields:
            value = row.get(field_name)
            if value in (None, ''):
                continue
            text_value = str(value)
            descriptor_values.append(text_value.lower())
            if 'deduction' in text_value.lower():
                matched_descriptor_pairs.append((field_name, text_value))
        if not matched_descriptor_pairs:
            continue

        raw_value = _num(row.get('deduction'))
        if raw_value != 0:
            classification = 'expense'
            reason = 'Текущий код берёт поле deduction, видит ненулевое значение и добавляет его в расход через abs(deduction).'
            expense_sum += abs(raw_value)
        else:
            classification = 'ignored'
            reason = 'Текущий код проверяет именно поле deduction. Здесь оно равно 0, поэтому строка в расчёт deduction не попадает.'
        raw_sum += raw_value

        item = {
            'date': str(_first(row, ['sale_dt', 'rr_dt', 'date', 'operation_dt'], date_to))[:10],
            'descriptors': matched_descriptor_pairs,
            'money_fields': [],
            'raw_value': round(raw_value, 2),
            'sign': '+' if raw_value > 0 else '-' if raw_value < 0 else '0',
            'classification': classification,
            'reason': reason,
        }
        for field_name in money_fields:
            if field_name in row and row.get(field_name) not in (None, ''):
                item['money_fields'].append((field_name, round(_num(row.get(field_name)), 2)))
        matched.append(item)

    return {
        'status': 'SUCCESS',
        'rows_count': len(matched),
        'items': matched[:max(1, int(limit or 10))],
        'raw_sum': round(raw_sum, 2),
        'expense_sum': round(expense_sum, 2),
        'income_sum': round(income_sum, 2),
    }


def _collect_ad_ids(count_payload):
    ids = []
    if isinstance(count_payload, dict):
        direct_id = count_payload.get('advertId') or count_payload.get('id') or count_payload.get('campaignId')
        if direct_id:
            ids.append(direct_id)
        groups = count_payload.get('adverts') or count_payload.get('data') or count_payload.get('list') or []
    else:
        groups = count_payload if isinstance(count_payload, list) else []
    for group in groups:
        if not isinstance(group, dict):
            continue
        direct_id = group.get('advertId') or group.get('id') or group.get('campaignId')
        if direct_id:
            ids.append(direct_id)
        items = group.get('advert_list') or group.get('advertList') or group.get('adverts') or group.get('list') or []
        if isinstance(items, dict):
            items = [items]
        for item in items:
            if isinstance(item, dict):
                advert_id = item.get('advertId') or item.get('id') or item.get('campaignId')
                if advert_id:
                    ids.append(advert_id)
    return list(dict.fromkeys(ids))


def _fetch_advert_ids(token, token_source='unknown'):
    payload, status = _get(f'{AD_API}/adv/v1/promotion/count', token, token_source=token_source)
    if status == 'SUCCESS':
        return _collect_ad_ids(payload), 'SUCCESS'
    if status == 'ERROR_404':
        return [], 'DISCOVERY_404'
    return [], status


def _extract_campaign_descriptors(count_payload):
    campaigns = {}
    roots = []
    if isinstance(count_payload, dict):
        roots.append(count_payload)
        groups = count_payload.get('adverts') or count_payload.get('data') or count_payload.get('list') or []
    else:
        groups = count_payload if isinstance(count_payload, list) else []
    if isinstance(groups, dict):
        groups = [groups]
    roots.extend([group for group in groups if isinstance(group, dict)])

    for root in roots:
        items = root.get('advert_list') or root.get('advertList') or root.get('adverts') or root.get('list') or []
        if isinstance(items, dict):
            items = [items]
        candidates = [root] + [item for item in items if isinstance(item, dict)]
        for item in candidates:
            advert_id = item.get('advertId') or item.get('id') or item.get('campaignId')
            if advert_id in (None, ''):
                continue
            key = str(advert_id)
            existing = campaigns.get(key) or {
                'advert_id': key,
                'name': '',
                'status': '',
                'type': '',
                'raw_keys': [],
            }
            name = item.get('name') or item.get('campaignName') or item.get('advertName') or ''
            status = item.get('status') or item.get('state') or item.get('campaignStatus') or ''
            campaign_type = item.get('type') or item.get('advertType') or item.get('campaignType') or ''
            if not existing['name'] and name:
                existing['name'] = str(name)
            if not existing['status'] and status not in (None, ''):
                existing['status'] = str(status)
            if not existing['type'] and campaign_type not in (None, ''):
                existing['type'] = str(campaign_type)
            keys = list(item.keys())[:20]
            if not existing['raw_keys'] and keys:
                existing['raw_keys'] = keys
            campaigns[key] = existing
    return [campaigns[key] for key in sorted(campaigns.keys(), key=lambda x: int(x) if str(x).isdigit() else str(x))]


def _local_advertising_period_stats(telegram_id, begin, end):
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute(
        '''
        SELECT
            COALESCE(campaign_id, ''),
            COALESCE(campaign_name, ''),
            ROUND(COALESCE(SUM(spend), 0), 2),
            COUNT(*),
            COUNT(DISTINCT substr(advert_date,1,10)),
            COUNT(DISTINCT CASE WHEN nm_id IS NULL THEN NULL ELSE CAST(nm_id AS TEXT) END),
            MIN(substr(advert_date,1,10)),
            MAX(substr(advert_date,1,10))
        FROM advertising
        WHERE telegram_id=?
          AND substr(advert_date,1,10) BETWEEN ? AND ?
        GROUP BY COALESCE(campaign_id, ''), COALESCE(campaign_name, '')
        ORDER BY SUM(spend) DESC, COALESCE(campaign_id, '')
        ''',
        (telegram_id, begin, end),
    )
    campaign_rows = cur.fetchall()

    cur.execute(
        '''
        SELECT
            substr(advert_date,1,10),
            ROUND(COALESCE(SUM(spend), 0), 2),
            COUNT(*),
            COUNT(DISTINCT COALESCE(campaign_id, ''))
        FROM advertising
        WHERE telegram_id=?
          AND substr(advert_date,1,10) BETWEEN ? AND ?
        GROUP BY substr(advert_date,1,10)
        ORDER BY substr(advert_date,1,10)
        ''',
        (telegram_id, begin, end),
    )
    day_rows = cur.fetchall()

    cur.execute(
        '''
        SELECT
            ROUND(COALESCE(SUM(spend), 0), 2),
            COUNT(*),
            COUNT(DISTINCT COALESCE(campaign_id, '')),
            MIN(substr(advert_date,1,10)),
            MAX(substr(advert_date,1,10))
        FROM advertising
        WHERE telegram_id=?
          AND substr(advert_date,1,10) BETWEEN ? AND ?
        ''',
        (telegram_id, begin, end),
    )
    total_spend, total_rows, distinct_campaigns, min_date, max_date = cur.fetchone()

    cur.execute(
        '''
        SELECT ROUND(COALESCE(SUM(amount), 0), 2), COUNT(*)
        FROM expenses
        WHERE telegram_id=?
          AND expense_type='advertising'
          AND substr(expense_date,1,10) BETWEEN ? AND ?
        ''',
        (telegram_id, begin, end),
    )
    expenses_total, expenses_rows = cur.fetchone()
    conn.close()

    campaigns = []
    campaign_ids = []
    for campaign_id, campaign_name, spend, rows_count, days_count, nm_ids_count, row_min_date, row_max_date in campaign_rows:
        campaign_key = str(campaign_id or '')
        if campaign_key:
            campaign_ids.append(campaign_key)
        campaigns.append({
            'advert_id': campaign_key,
            'name': str(campaign_name or ''),
            'spend': round(float(spend or 0), 2),
            'rows': int(rows_count or 0),
            'days': int(days_count or 0),
            'nm_ids': int(nm_ids_count or 0),
            'period_begin': row_min_date,
            'period_end': row_max_date,
        })

    daily = []
    dates = []
    for advert_date, spend, rows_count, campaigns_count in day_rows:
        if advert_date:
            dates.append(str(advert_date))
        daily.append({
            'date': str(advert_date),
            'spend': round(float(spend or 0), 2),
            'rows': int(rows_count or 0),
            'campaigns': int(campaigns_count or 0),
        })

    return {
        'campaigns': campaigns,
        'campaign_ids': campaign_ids,
        'campaigns_count': int(len(campaign_ids)),
        'rows_count': int(total_rows or 0),
        'daily': daily,
        'dates': dates,
        'total_spend': round(float(total_spend or 0), 2),
        'expenses_total': round(float(expenses_total or 0), 2),
        'expenses_rows': int(expenses_rows or 0),
        'min_date': min_date,
        'max_date': max_date,
    }


def compare_advertising_period(telegram_id, token, begin, end, token_source='unknown'):
    result = {
        'status': 'SUCCESS',
        'period_begin': begin,
        'period_end': end,
        'count_status': None,
        'fullstats_status': None,
        'fullstats_total_spend': 0.0,
        'local_total_spend': 0.0,
        'delta_total': 0.0,
        'campaigns_count_local': 0,
        'campaigns_count_fullstats': 0,
        'campaigns_compared': 0,
        'campaigns': [],
        'days': [],
        'top_delta_days': [],
        'notes': [],
    }

    local = _local_advertising_period_stats(telegram_id, begin, end)
    local_campaign_map = {str(item.get('advert_id') or ''): item for item in (local.get('campaigns') or []) if str(item.get('advert_id') or '')}
    local_day_map = {str(item.get('date') or ''): item for item in (local.get('daily') or []) if str(item.get('date') or '')}
    local_ids = [int(campaign_id) for campaign_id in (local.get('campaign_ids') or []) if str(campaign_id).isdigit()]

    result['local_total_spend'] = round(float(local.get('total_spend') or 0), 2)
    result['campaigns_count_local'] = int(local.get('campaigns_count') or 0)

    found_ids = []
    count_payload, count_status = _get(
        f'{AD_API}/adv/v1/promotion/count',
        token,
        token_source=token_source,
        caller='compare_advertising_period->promotion/count'
    )
    result['count_status'] = count_status
    if count_status == 'SUCCESS':
        campaign_descriptors = _extract_campaign_descriptors(count_payload)
        found_ids = [int(item['advert_id']) for item in campaign_descriptors if str(item.get('advert_id') or '').isdigit()]
    else:
        result['notes'].append('promotion/count не отработал, сравнение строится по campaign_id из local advertising.')

    batch_ids = []
    seen_ids = set()
    for advert_id in found_ids + local_ids:
        if advert_id in seen_ids:
            continue
        seen_ids.add(advert_id)
        batch_ids.append(advert_id)

    if not batch_ids:
        result['notes'].append('В периоде нет campaign_id для сравнения.')
        return result

    payload, fullstats_status = _fetch_fullstats_batch(
        token,
        batch_ids,
        begin,
        end,
        timeout=120,
        token_source=token_source,
    )
    result['fullstats_status'] = fullstats_status
    if fullstats_status != 'SUCCESS':
        result['status'] = fullstats_status
        result['delta_total'] = round(result['local_total_spend'] - result['fullstats_total_spend'], 2)
        result['notes'].append('fullstats не отработал, поэтому показана только локальная часть сравнения.')
        return result

    fullstats_campaigns = {}
    fullstats_days = {}
    for row in _iter_fullstats(payload) or []:
        campaign_id = row.get('campaign_id')
        if campaign_id in (None, ''):
            continue
        advert_id = str(campaign_id)
        advert_date = str(row.get('date') or '')[:10]
        spend = round(float(_num(row.get('spend'))), 2)
        bucket = fullstats_campaigns.setdefault(advert_id, {
            'advert_id': advert_id,
            'spend': 0.0,
        })
        bucket['spend'] = round(bucket['spend'] + spend, 2)
        if advert_date:
            fullstats_days[advert_date] = round(float(fullstats_days.get(advert_date) or 0) + spend, 2)

    result['campaigns_count_fullstats'] = int(len(fullstats_campaigns))

    all_campaign_ids = sorted(
        set(list(fullstats_campaigns.keys()) + list(local_campaign_map.keys())),
        key=lambda value: int(value) if str(value).isdigit() else str(value),
    )
    campaigns = []
    for advert_id in all_campaign_ids:
        fullstats_spend = round(float((fullstats_campaigns.get(advert_id) or {}).get('spend') or 0), 2)
        local_item = local_campaign_map.get(advert_id) or {}
        saved_to_advertising = round(float(local_item.get('spend') or 0), 2)
        ratio = None
        if fullstats_spend > 0:
            ratio = round(saved_to_advertising / fullstats_spend, 6)
        elif saved_to_advertising > 0:
            ratio = None
        campaigns.append({
            'advert_id': advert_id,
            'fullstats_spend': fullstats_spend,
            'saved_to_advertising': saved_to_advertising,
            'advertising_rows': int(local_item.get('rows') or 0),
            'advertising_dates': int(local_item.get('days') or 0),
            'advertising_nm_ids': int(local_item.get('nm_ids') or 0),
            'ratio': ratio,
            'delta': round(saved_to_advertising - fullstats_spend, 2),
            'in_fullstats': advert_id in fullstats_campaigns,
            'in_local': advert_id in local_campaign_map,
        })

    campaigns.sort(
        key=lambda item: (
            -float(item.get('delta') or 0),
            -abs(float(item.get('delta') or 0)),
            -float(item.get('saved_to_advertising') or 0),
            item.get('advert_id') or '',
        )
    )
    result['campaigns'] = campaigns
    result['campaigns_compared'] = int(len(campaigns))

    all_dates = sorted(set(list(fullstats_days.keys()) + list(local_day_map.keys())))
    days = []
    for advert_date in all_dates:
        fullstats_day_spend = round(float(fullstats_days.get(advert_date) or 0), 2)
        local_day_spend = round(float((local_day_map.get(advert_date) or {}).get('spend') or 0), 2)
        days.append({
            'date': advert_date,
            'fullstats_day_spend': fullstats_day_spend,
            'local_day_spend': local_day_spend,
            'delta': round(local_day_spend - fullstats_day_spend, 2),
        })

    result['days'] = days
    result['top_delta_days'] = sorted(
        days,
        key=lambda item: (
            -float(item.get('delta') or 0),
            -abs(float(item.get('delta') or 0)),
            item.get('date') or '',
        )
    )[:20]
    result['fullstats_total_spend'] = round(sum(item.get('fullstats_spend') or 0 for item in campaigns), 2)
    result['local_total_spend'] = round(sum(item.get('saved_to_advertising') or 0 for item in campaigns), 2)
    result['delta_total'] = round(result['local_total_spend'] - result['fullstats_total_spend'], 2)

    if any((not item.get('in_fullstats')) and (item.get('saved_to_advertising') or 0) > 0 for item in campaigns):
        result['notes'].append('Есть campaign_id с расходом в local advertising, но без строк в fullstats за период.')
    if any((not item.get('in_local')) and (item.get('fullstats_spend') or 0) > 0 for item in campaigns):
        result['notes'].append('Есть campaign_id с расходом в fullstats, но без строк в local advertising.')

    return result


def audit_advertising_period(telegram_id, token, days=30, token_source='unknown'):
    begin, end = _normalize_period_dates(days)
    result = {
        'status': 'SUCCESS',
        'period_begin': begin,
        'period_end': end,
        'count_status': None,
        'fullstats_status': None,
        'campaigns_found': 0,
        'campaigns_loaded': 0,
        'campaigns_in_local': 0,
        'fullstats_rows': 0,
        'api_total_spend': 0.0,
        'local_total_spend': 0.0,
        'local_expenses_total': 0.0,
        'campaigns': [],
        'api_daily': [],
        'local_daily': [],
        'missing_from_fullstats': [],
        'missing_in_local': [],
        'local_only': [],
        'notes': [],
    }

    count_payload, count_status = _get(
        f'{AD_API}/adv/v1/promotion/count',
        token,
        token_source=token_source,
        caller='audit_advertising_period->promotion/count'
    )
    result['count_status'] = count_status
    campaign_descriptors = _extract_campaign_descriptors(count_payload)
    found_ids = [int(item['advert_id']) for item in campaign_descriptors if str(item.get('advert_id') or '').isdigit()]
    result['campaigns_found'] = len(found_ids)
    result['found_campaigns'] = campaign_descriptors

    local = _local_advertising_period_stats(telegram_id, begin, end)
    result['local_total_spend'] = local['total_spend']
    result['local_expenses_total'] = local['expenses_total']
    result['campaigns_in_local'] = local['campaigns_count']
    result['local_daily'] = local['daily']
    result['local_period'] = {
        'min_date': local['min_date'],
        'max_date': local['max_date'],
        'rows_count': local['rows_count'],
        'expenses_rows': local['expenses_rows'],
    }

    if count_status != 'SUCCESS':
        result['status'] = count_status
        result['notes'].append('promotion/count не отработал, поэтому сравнение с fullstats недоступно.')
        return result

    if not found_ids:
        result['notes'].append('promotion/count не вернул ни одной кампании.')
        return result

    payload, fullstats_status = _fetch_fullstats_batch(
        token,
        found_ids,
        begin,
        end,
        timeout=120,
        token_source=token_source,
    )
    result['fullstats_status'] = fullstats_status
    if fullstats_status != 'SUCCESS':
        result['status'] = fullstats_status
        result['notes'].append('fullstats не отработал, поэтому показано только локальное состояние БД.')
        return result

    api_campaigns = {}
    api_daily = {}
    api_ids_received = set()
    for row in _iter_fullstats(payload) or []:
        campaign_id = row.get('campaign_id')
        if campaign_id in (None, ''):
            continue
        campaign_key = str(campaign_id)
        advert_date = str(row.get('date') or '')[:10]
        spend = round(float(_num(row.get('spend'))), 2)
        views = int(_int(row.get('views')))
        clicks = int(_int(row.get('clicks')))
        orders = int(_int(row.get('orders')))
        sum_price = round(float(_num(row.get('sum_price'))), 2)
        api_ids_received.add(int(campaign_id))
        bucket = api_campaigns.setdefault(campaign_key, {
            'advert_id': campaign_key,
            'name': str(row.get('campaign_name') or ''),
            'spend': 0.0,
            'views': 0,
            'clicks': 0,
            'orders': 0,
            'sum_price': 0.0,
            'days': set(),
            'rows': 0,
        })
        if not bucket['name'] and row.get('campaign_name'):
            bucket['name'] = str(row.get('campaign_name') or '')
        bucket['spend'] = round(bucket['spend'] + spend, 2)
        bucket['views'] += views
        bucket['clicks'] += clicks
        bucket['orders'] += orders
        bucket['sum_price'] = round(bucket['sum_price'] + sum_price, 2)
        bucket['rows'] += 1
        if advert_date:
            bucket['days'].add(advert_date)
            day_bucket = api_daily.setdefault(advert_date, {'date': advert_date, 'spend': 0.0, 'rows': 0, 'campaigns': set()})
            day_bucket['spend'] = round(day_bucket['spend'] + spend, 2)
            day_bucket['rows'] += 1
            day_bucket['campaigns'].add(campaign_key)

    local_campaign_map = {item['advert_id']: item for item in local['campaigns'] if item.get('advert_id')}
    found_map = {item['advert_id']: item for item in campaign_descriptors if item.get('advert_id')}

    comparison = []
    all_ids = sorted(
        set(list(api_campaigns.keys()) + list(local_campaign_map.keys()) + list(found_map.keys())),
        key=lambda value: int(value) if str(value).isdigit() else str(value),
    )
    for advert_id in all_ids:
        api_item = api_campaigns.get(advert_id) or {}
        local_item = local_campaign_map.get(advert_id) or {}
        found_item = found_map.get(advert_id) or {}
        api_spend = round(float(api_item.get('spend') or 0), 2)
        local_spend = round(float(local_item.get('spend') or 0), 2)
        comparison.append({
            'advert_id': advert_id,
            'name': str(api_item.get('name') or local_item.get('name') or found_item.get('name') or ''),
            'status': str(found_item.get('status') or ''),
            'type': str(found_item.get('type') or ''),
            'api_spend': api_spend,
            'local_spend': local_spend,
            'delta': round(api_spend - local_spend, 2),
            'api_days': len(api_item.get('days') or []),
            'local_days': int(local_item.get('days') or 0),
            'api_rows': int(api_item.get('rows') or 0),
            'local_rows': int(local_item.get('rows') or 0),
            'in_found': advert_id in found_map,
            'in_api': advert_id in api_campaigns,
            'in_local': advert_id in local_campaign_map,
        })

    result['campaigns'] = sorted(comparison, key=lambda item: (-float(item['api_spend'] or 0), -float(item['local_spend'] or 0), item['advert_id']))
    result['campaigns_loaded'] = len(api_campaigns)
    result['fullstats_rows'] = int(sum(item.get('api_rows') or 0 for item in result['campaigns']))
    result['api_total_spend'] = round(sum(item.get('api_spend') or 0 for item in result['campaigns']), 2)
    result['api_daily'] = [
        {
            'date': day_key,
            'spend': round(float(day_value.get('spend') or 0), 2),
            'rows': int(day_value.get('rows') or 0),
            'campaigns': len(day_value.get('campaigns') or []),
        }
        for day_key, day_value in sorted(api_daily.items())
    ]
    result['missing_from_fullstats'] = [item for item in result['campaigns'] if item['in_found'] and not item['in_api']]
    result['missing_in_local'] = [item for item in result['campaigns'] if item['in_api'] and not item['in_local']]
    result['local_only'] = [item for item in result['campaigns'] if item['in_local'] and not item['in_api']]

    if local['min_date'] and local['min_date'] > begin:
        result['notes'].append(
            f"Локальная advertising начинается с {local['min_date']}, поэтому период {begin} — {end} в БД покрыт не полностью."
        )
    if result['missing_from_fullstats']:
        result['notes'].append('Часть campaign_id найдена через promotion/count, но не вернулась в fullstats за выбранный период.')
    if result['missing_in_local']:
        result['notes'].append('Часть campaign_id есть в Advertising API, но отсутствует в локальной advertising.')
    if result['local_total_spend'] != result['local_expenses_total']:
        result['notes'].append('Сумма advertising и expenses(advertising) в локальной БД различается.')

    return result


def _try_num(value):
    if value is None or isinstance(value, bool):
        return False, 0.0
    if isinstance(value, (int, float)):
        return True, float(value)
    text = str(value).strip().replace(',', '.')
    if not text:
        return False, 0.0
    try:
        return True, float(text)
    except Exception:
        return False, 0.0


def _fullstats_payload_campaigns(payload):
    if isinstance(payload, dict):
        payload = payload.get('data') or payload.get('adverts') or payload.get('campaigns') or []
    return payload if isinstance(payload, list) else []


def _looks_like_money_field(field_name):
    name = str(field_name or '').strip()
    if not name:
        return False
    lowered = name.lower()
    return (
        lowered in ('sum', 'expenses', 'advertexpenses', 'advertsum', 'payment', 'balance', 'cost', 'price', 'sum_price', 'sumprice', 'spend')
        or 'expense' in lowered
        or 'payment' in lowered
        or 'balance' in lowered
        or 'spend' in lowered
        or 'cost' in lowered
        or 'price' in lowered
        or lowered == 'sum'
    )


def _fieldaudit_sort_key(field_name):
    priority = ['sum', 'expenses', 'advertExpenses', 'advertSum', 'payment', 'balance', 'cost', 'price', 'sum_price', 'sumPrice', 'spend']
    try:
        return (0, priority.index(field_name))
    except ValueError:
        return (1, str(field_name or '').lower())


def _collect_fullstats_money_fields(node, fields_sum, fields_seen):
    if isinstance(node, dict):
        for key, value in node.items():
            if _looks_like_money_field(key):
                ok, number = _try_num(value)
                if ok:
                    fields_sum[str(key)] += float(number)
                    fields_seen.add(str(key))
            if isinstance(value, (dict, list)):
                _collect_fullstats_money_fields(value, fields_sum, fields_seen)
    elif isinstance(node, list):
        for item in node:
            _collect_fullstats_money_fields(item, fields_sum, fields_seen)


def _fullstats_spend_value(node):
    if not isinstance(node, dict):
        return 0.0
    return _num(node.get('sum') or node.get('spend') or node.get('cost'))


def _fullstats_direct_item_spend(item):
    if not isinstance(item, dict):
        return 0.0, 'none'
    for key in ('sum', 'spend', 'cost'):
        value = item.get(key)
        if value not in (None, ''):
            return _num(value), f'item.{key}'
    return 0.0, 'none'


def _fullstats_direct_app_spend(app):
    if not isinstance(app, dict):
        return 0.0, 'none'
    for key in ('sum', 'spend', 'cost'):
        value = app.get(key)
        if value not in (None, ''):
            return _num(value), f'app.{key}'
    return 0.0, 'none'


def _fullstats_direct_day_spend(day):
    if not isinstance(day, dict):
        return 0.0, 'none'
    for key in ('sum', 'spend', 'cost'):
        value = day.get(key)
        if value not in (None, ''):
            return _num(value), f'day.{key}'
    return 0.0, 'none'


def _fullstats_row_sum_price(item, app, day):
    if isinstance(item, dict):
        value = item.get('sum_price')
        if value not in (None, ''):
            return _num(value)
        value = item.get('sumPrice')
        if value not in (None, ''):
            return _num(value)
    if isinstance(app, dict):
        value = app.get('sum_price')
        if value not in (None, ''):
            return _num(value)
    if isinstance(day, dict):
        value = day.get('sum_price')
        if value not in (None, ''):
            return _num(value)
    return 0.0


def _money_close(left, right, eps=0.01):
    return abs(_num(left) - _num(right)) <= eps


def _build_fullstats_row(d, campaign_id, campaign_name, article, nm_id, views, clicks, orders, sum_price, spend, spend_source='none', app_nm_count=0, aggregate_key=None, app_type=None, name=None):
    row = {
        'date': d,
        'campaign_id': campaign_id,
        'campaign_name': campaign_name,
        'article': article,
        'nm_id': nm_id,
        'app_type': app_type,
        'name': name,
        'views': _int(views),
        'clicks': _int(clicks),
        'orders': _int(orders),
        'sum_price': _num(sum_price),
        'spend': _num(spend),
    }
    if spend_source is not None:
        row['spend_source'] = spend_source
    if app_nm_count is not None:
        row['app_nm_count'] = int(app_nm_count or 0)
    if aggregate_key:
        row['aggregate_key'] = aggregate_key
    return row


def _set_fullstats_trace_fields(row, campaign_id, date_value, app_type, day_index, app_index, item_index=None):
    if not isinstance(row, dict):
        return row
    row['trace_campaign_id'] = str(campaign_id) if campaign_id not in (None, '') else None
    row['trace_date'] = str(date_value)[:10] if date_value not in (None, '') else None
    row['trace_app_type'] = str(app_type or '').strip() or None
    row['trace_day_index'] = int(day_index or 0)
    row['trace_app_index'] = int(app_index or 0)
    row['trace_item_index'] = None if item_index is None else int(item_index)
    return row


def _allocate_weighted_amount(total_amount, rows, key_fields):
    eligible_rows = [row for row in (rows or []) if row is not None]
    total_amount = round(_num(total_amount), 2)
    if total_amount <= 0 or not eligible_rows:
        return [], 'none'

    weights = []
    method = 'equal'
    for field_name, field_method in key_fields:
        values = [max(0.0, _num(row.get(field_name))) for row in eligible_rows]
        total_weight = round(sum(values), 6)
        if total_weight > 0:
            weights = values
            method = field_method
            break
    if not weights:
        weights = [1.0] * len(eligible_rows)

    allocated = []
    running_total = 0.0
    weight_total = float(sum(weights) or 0)
    for index, row in enumerate(eligible_rows):
        if index == len(eligible_rows) - 1:
            amount = round(total_amount - running_total, 2)
        else:
            ratio = (weights[index] / weight_total) if weight_total > 0 else (1.0 / len(eligible_rows))
            amount = round(total_amount * ratio, 2)
            running_total = round(running_total + amount, 2)
        allocated.append((row, amount))
    return allocated, method


def _real_fullstats_nm_rows(rows):
    result = []
    for row in rows or []:
        nm_id = row.get('nm_id')
        try:
            if nm_id in (None, ''):
                continue
            if int(str(nm_id).strip()) > 0:
                result.append(row)
        except Exception:
            continue
    return result


def _allocate_parent_spend_to_nm_rows(rows, total_amount, source_level, source_field, aggregate_prefix, aggregate_parts):
    eligible_rows = [
        row for row in _real_fullstats_nm_rows(rows)
        if str(row.get('spend_source') or 'none') == 'none'
    ]
    allocations, method = _allocate_weighted_amount(
        total_amount,
        eligible_rows,
        (
            ('sum_price', 'sum_price'),
            ('orders', 'orders'),
            ('clicks', 'clicks'),
        ),
    )
    if not allocations:
        return False, 'none'

    for row, amount in allocations:
        row['spend'] = round(amount, 2)
        row['spend_source'] = source_field
        row['allocation_source'] = source_level
        row['allocation_method'] = method
        row['aggregate_key'] = f"{aggregate_prefix}:{':'.join(str(part) for part in aggregate_parts)}:{row.get('nm_id')}"
    return True, method


def _iter_fullstats_rows(payload, include_trace=False):
    if isinstance(payload, dict):
        payload = payload.get('data') or payload.get('adverts') or payload.get('campaigns') or []
    if not isinstance(payload, list):
        return

    aggregate_seq = 0

    def make_row(*args, **kwargs):
        row = _build_fullstats_row(*args, **kwargs)
        if not include_trace:
            row.pop('spend_source', None)
            row.pop('app_nm_count', None)
            row.pop('allocation_source', None)
            row.pop('allocation_method', None)
            row.pop('trace_campaign_id', None)
            row.pop('trace_date', None)
            row.pop('trace_app_type', None)
            row.pop('trace_day_index', None)
            row.pop('trace_app_index', None)
            row.pop('trace_item_index', None)
        return row

    for camp_index, camp in enumerate(payload):
        if not isinstance(camp, dict):
            continue
        cid = camp.get('advertId') or camp.get('id') or camp.get('campaignId')
        cname = camp.get('name') or camp.get('campaignName') or ''
        days_rows = camp.get('days') or camp.get('statistics') or camp.get('stats') or [camp]
        if not isinstance(days_rows, list):
            days_rows = [camp]

        for day_index, day in enumerate(days_rows):
            if not isinstance(day, dict):
                continue

            d = str(day.get('date') or day.get('day') or _today())[:10]
            apps = day.get('apps') or day.get('items') or day.get('nm') or [day]
            if not isinstance(apps, list):
                apps = [day]

            day_spend, day_spend_source = _fullstats_direct_day_spend(day)
            day_rows = []

            for app_index, app in enumerate(apps):
                app_node = app if isinstance(app, dict) else day
                raw_nm_items = app_node.get('nm') or app_node.get('nms') or app_node.get('items')
                explicit_nm = raw_nm_items is not None
                if explicit_nm and not isinstance(raw_nm_items, list):
                    raw_nm_items = [raw_nm_items]
                nm_items = raw_nm_items if explicit_nm else []
                app_spend, app_spend_source = _fullstats_direct_app_spend(app_node)
                current_app_type = app_node.get('appType') or app_node.get('type') or app_node.get('appTypeName') or app_node.get('name')

                if explicit_nm:
                    app_rows = []
                    spendful_rows = []
                    for item_index, item in enumerate(nm_items):
                        if not isinstance(item, dict):
                            continue
                        spend, spend_source = _fullstats_direct_item_spend(item)
                        row = make_row(
                            d,
                            cid,
                            cname,
                            item.get('supplierArticle') or item.get('article'),
                            item.get('nmId') or item.get('nm') or item.get('id'),
                            item.get('views') or item.get('openCardCount') or app_node.get('views') or day.get('views'),
                            item.get('clicks') or app_node.get('clicks') or day.get('clicks'),
                            item.get('orders') or item.get('atbs') or app_node.get('orders') or day.get('orders'),
                            _fullstats_row_sum_price(item, app_node, day),
                            spend,
                            spend_source=spend_source,
                            app_nm_count=len(nm_items),
                            app_type=current_app_type,
                            name=item.get('name') or item.get('nmName') or item.get('subjectName') or item.get('supplierArticle') or item.get('article'),
                        )
                        if include_trace:
                            _set_fullstats_trace_fields(row, cid, d, current_app_type, day_index, app_index, item_index)
                        app_rows.append(row)
                        if spend_source != 'none':
                            spendful_rows.append(row)

                    spendful_total = round(sum(_num(row.get('spend')) for row in spendful_rows), 2)
                    real_nm_rows = _real_fullstats_nm_rows(app_rows)
                    parent_spend = None
                    parent_source = 'none'
                    if app_spend_source != 'none':
                        parent_spend = app_spend
                        parent_source = app_spend_source
                    elif day_spend_source != 'none':
                        parent_spend = day_spend
                        parent_source = day_spend_source

                    if app_spend_source != 'none':
                        remaining_app_spend = round(max(0.0, _num(app_spend) - spendful_total), 2)
                        allocated, _ = _allocate_parent_spend_to_nm_rows(
                            app_rows,
                            remaining_app_spend,
                            'app',
                            app_spend_source,
                            'app_alloc',
                            (cid, d, current_app_type or '-', app_index),
                        )
                        if remaining_app_spend > 0 and not allocated:
                            aggregate_row = make_row(
                                d,
                                cid,
                                cname,
                                None,
                                None,
                                app_node.get('views') or day.get('views'),
                                app_node.get('clicks') or day.get('clicks'),
                                app_node.get('orders') or day.get('orders'),
                                _fullstats_row_sum_price(app_node, app_node, day),
                                remaining_app_spend,
                                spend_source=app_spend_source,
                                app_nm_count=len(nm_items),
                                aggregate_key=f'agg_app_remainder:{camp_index}:{day_index}:{app_index}',
                                app_type=current_app_type,
                                name=app_node.get('name') or app_node.get('appName'),
                            )
                            if include_trace:
                                _set_fullstats_trace_fields(aggregate_row, cid, d, current_app_type, day_index, app_index, None)
                            app_rows.append(aggregate_row)

                    day_rows.extend(app_rows)
                    continue

                app_article = app_node.get('supplierArticle') or app_node.get('article')
                app_nm_id = app_node.get('nmId') or app_node.get('nm') or app_node.get('id')
                if app_spend_source != 'none' or app_article not in (None, '') or app_nm_id not in (None, ''):
                    fallback_nm_id = app_nm_id if app_nm_id not in (None, '') else None
                    day_rows.append(make_row(
                        d,
                        cid,
                        cname,
                        app_article,
                        fallback_nm_id,
                        app_node.get('views') or day.get('views'),
                        app_node.get('clicks') or day.get('clicks'),
                        app_node.get('orders') or day.get('orders'),
                        _fullstats_row_sum_price(app_node, app_node, day),
                        app_spend,
                        spend_source=app_spend_source,
                        app_nm_count=1,
                        aggregate_key=f'agg_app_flat:{camp_index}:{day_index}:{app_index}',
                        app_type=current_app_type,
                        name=app_node.get('name') or app_node.get('appName') or app_article,
                    ))
                    if include_trace and day_rows:
                        _set_fullstats_trace_fields(day_rows[-1], cid, d, current_app_type, day_index, app_index, None)

            spendful_day_rows = [row for row in day_rows if str(row.get('spend_source') or 'none') != 'none']
            if day_spend_source != 'none':
                spendful_day_total = round(sum(_num(row.get('spend')) for row in spendful_day_rows), 2)
                remaining_day_spend = round(max(0.0, _num(day_spend) - spendful_day_total), 2)
                allocated_day_spend, _ = _allocate_parent_spend_to_nm_rows(
                    day_rows,
                    remaining_day_spend,
                    'day',
                    day_spend_source,
                    'day_alloc',
                    (cid, d),
                )
                if remaining_day_spend > 0 and not allocated_day_spend:
                    aggregate_row = make_row(
                        d,
                        cid,
                        cname,
                        None,
                        None,
                        day.get('views'),
                        day.get('clicks'),
                        day.get('orders'),
                        _fullstats_row_sum_price(day, day, day),
                        remaining_day_spend,
                        spend_source=day_spend_source,
                        app_nm_count=len(apps),
                        aggregate_key=f'agg_day_remainder:{camp_index}:{day_index}',
                    )
                    if include_trace:
                        _set_fullstats_trace_fields(aggregate_row, cid, d, None, day_index, -1, None)
                    day_rows.append(aggregate_row)

            for row in day_rows:
                yield row


def _iter_fullstats_trace(payload):
    yield from _iter_fullstats_rows(payload, include_trace=True)


def _local_advertising_saved_by_campaign(telegram_id, begin, end):
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        '''
        SELECT COALESCE(campaign_id, ''), ROUND(COALESCE(SUM(spend), 0), 2)
        FROM advertising
        WHERE telegram_id=? AND substr(advert_date,1,10) BETWEEN ? AND ?
        GROUP BY COALESCE(campaign_id, '')
        ''',
        (telegram_id, begin, end),
    )
    rows = cur.fetchall()
    conn.close()
    return {str(campaign_id): round(float(total_spend or 0), 2) for campaign_id, total_spend in rows if str(campaign_id) != ''}


def ads_fullstats_field_audit(telegram_id, token, begin, end, token_source='unknown'):
    result = {
        'status': 'SUCCESS',
        'period_begin': str(begin),
        'period_end': str(end),
        'count_status': None,
        'fullstats_status': None,
        'campaigns_found': 0,
        'campaigns_returned': 0,
        'raw_money_fields': [],
        'used_for_save': {
            'advertising.sum_price': ['sum_price', 'sumPrice'],
            'advertising.spend': ['sum', 'spend', 'cost'],
            'expenses.amount(source=api_advertising)': ['advertising.spend when spend > 0'],
        },
        'campaigns': [],
        'notes': [],
    }

    count_payload, count_status = _get(
        f'{AD_API}/adv/v1/promotion/count',
        token,
        token_source=token_source,
        caller='ads_fullstats_field_audit->promotion/count'
    )
    result['count_status'] = count_status
    campaign_descriptors = _extract_campaign_descriptors(count_payload)
    descriptor_map = {str(item.get('advert_id')): item for item in campaign_descriptors if item.get('advert_id') not in (None, '')}
    found_ids = [int(item['advert_id']) for item in campaign_descriptors if str(item.get('advert_id') or '').isdigit()]
    result['campaigns_found'] = len(found_ids)

    if count_status != 'SUCCESS':
        result['status'] = count_status
        result['notes'].append('promotion/count не отработал, fieldaudit завершён только статусом вызова.')
        return result

    if not found_ids:
        result['notes'].append('promotion/count не вернул campaign_id для fieldaudit.')
        return result

    payload, fullstats_status = _fetch_fullstats_batch(
        token,
        found_ids,
        begin,
        end,
        timeout=120,
        token_source=token_source,
    )
    result['fullstats_status'] = fullstats_status
    if fullstats_status != 'SUCCESS':
        result['status'] = fullstats_status
        result['notes'].append('fullstats не отработал, raw audit по полям недоступен.')
        return result

    raw_campaigns = {}
    all_fields = set()
    for campaign in _fullstats_payload_campaigns(payload):
        if not isinstance(campaign, dict):
            continue
        campaign_id = campaign.get('advertId') or campaign.get('id') or campaign.get('campaignId')
        if campaign_id in (None, ''):
            continue
        campaign_key = str(campaign_id)
        bucket = raw_campaigns.setdefault(campaign_key, {
            'advert_id': campaign_key,
            'campaign_name': str(campaign.get('name') or campaign.get('campaignName') or ''),
            'raw_money_fields': defaultdict(float),
            'raw_fields_present': set(),
            'saved_to_advertising': 0.0,
            'normalized_spend_used_now': 0.0,
            'normalized_sum_price_used_now': 0.0,
        })
        _collect_fullstats_money_fields(campaign, bucket['raw_money_fields'], bucket['raw_fields_present'])
        all_fields.update(bucket['raw_fields_present'])

    for row in _iter_fullstats(payload) or []:
        campaign_id = row.get('campaign_id')
        if campaign_id in (None, ''):
            continue
        campaign_key = str(campaign_id)
        bucket = raw_campaigns.setdefault(campaign_key, {
            'advert_id': campaign_key,
            'campaign_name': str(row.get('campaign_name') or ''),
            'raw_money_fields': defaultdict(float),
            'raw_fields_present': set(),
            'saved_to_advertising': 0.0,
            'normalized_spend_used_now': 0.0,
            'normalized_sum_price_used_now': 0.0,
        })
        if not bucket['campaign_name'] and row.get('campaign_name'):
            bucket['campaign_name'] = str(row.get('campaign_name') or '')
        bucket['normalized_spend_used_now'] = round(bucket['normalized_spend_used_now'] + float(_num(row.get('spend'))), 2)
        bucket['normalized_sum_price_used_now'] = round(bucket['normalized_sum_price_used_now'] + float(_num(row.get('sum_price'))), 2)

    local_saved = _local_advertising_saved_by_campaign(telegram_id, begin, end)
    for campaign_key, amount in local_saved.items():
        bucket = raw_campaigns.setdefault(campaign_key, {
            'advert_id': campaign_key,
            'campaign_name': '',
            'raw_money_fields': defaultdict(float),
            'raw_fields_present': set(),
            'saved_to_advertising': 0.0,
            'normalized_spend_used_now': 0.0,
            'normalized_sum_price_used_now': 0.0,
        })
        bucket['saved_to_advertising'] = round(float(amount or 0), 2)

    result['campaigns_returned'] = len(raw_campaigns)
    result['raw_money_fields'] = sorted(all_fields, key=_fieldaudit_sort_key)

    campaign_ids = sorted(
        set(list(raw_campaigns.keys()) + list(descriptor_map.keys())),
        key=lambda value: int(value) if str(value).isdigit() else str(value),
    )
    for campaign_key in campaign_ids:
        bucket = raw_campaigns.get(campaign_key)
        descriptor = descriptor_map.get(campaign_key) or {}
        campaign_name = ''
        if bucket:
            campaign_name = bucket.get('campaign_name') or ''
        if not campaign_name:
            campaign_name = str(descriptor.get('name') or '')
        item = {
            'advert_id': campaign_key,
            'campaign_name': campaign_name,
            'raw_money_fields': {},
            'saved_to_advertising': round(float(bucket.get('saved_to_advertising') or 0), 2) if bucket else 0.0,
            'normalized_spend_used_now': round(float(bucket.get('normalized_spend_used_now') or 0), 2) if bucket else 0.0,
            'normalized_sum_price_used_now': round(float(bucket.get('normalized_sum_price_used_now') or 0), 2) if bucket else 0.0,
            'in_fullstats': bool(bucket),
            'in_local_advertising': campaign_key in local_saved,
        }
        if bucket:
            item['raw_money_fields'] = {
                field_name: round(float(field_value or 0), 2)
                for field_name, field_value in sorted(bucket['raw_money_fields'].items(), key=lambda pair: _fieldaudit_sort_key(pair[0]))
            }
        result['campaigns'].append(item)

    if not result['raw_money_fields']:
        result['notes'].append('В raw payload fullstats не найдено ни одного денежного поля по текущему детектору.')
    return result


def ads_fullstats_level_audit(telegram_id, token, begin, end, token_source='unknown'):
    result = {
        'status': 'SUCCESS',
        'period_begin': str(begin),
        'period_end': str(end),
        'count_status': None,
        'fullstats_status': None,
        'campaigns_found': 0,
        'campaigns_returned': 0,
        'campaigns': [],
        'notes': [],
    }

    count_payload, count_status = _get(
        f'{AD_API}/adv/v1/promotion/count',
        token,
        token_source=token_source,
        caller='ads_fullstats_level_audit->promotion/count'
    )
    result['count_status'] = count_status
    campaign_descriptors = _extract_campaign_descriptors(count_payload)
    descriptor_map = {str(item.get('advert_id')): item for item in campaign_descriptors if item.get('advert_id') not in (None, '')}
    found_ids = [int(item['advert_id']) for item in campaign_descriptors if str(item.get('advert_id') or '').isdigit()]
    result['campaigns_found'] = len(found_ids)

    if count_status != 'SUCCESS':
        result['status'] = count_status
        result['notes'].append('promotion/count не отработал, levelaudit завершён только статусом вызова.')
        return result

    if not found_ids:
        result['notes'].append('promotion/count не вернул campaign_id для levelaudit.')
        return result

    payload, fullstats_status = _fetch_fullstats_batch(
        token,
        found_ids,
        begin,
        end,
        timeout=120,
        token_source=token_source,
    )
    result['fullstats_status'] = fullstats_status
    if fullstats_status != 'SUCCESS':
        result['status'] = fullstats_status
        result['notes'].append('fullstats не отработал, level audit недоступен.')
        return result

    campaign_buckets = {}
    for campaign in _fullstats_payload_campaigns(payload):
        if not isinstance(campaign, dict):
            continue
        campaign_id = campaign.get('advertId') or campaign.get('id') or campaign.get('campaignId')
        if campaign_id in (None, ''):
            continue
        campaign_key = str(campaign_id)
        bucket = campaign_buckets.setdefault(campaign_key, {
            'advert_id': campaign_key,
            'campaign_name': str(campaign.get('name') or campaign.get('campaignName') or ''),
            'advert_level_sum': 0.0,
            'days_level_sum': 0.0,
            'apps_level_sum': 0.0,
            'nms_level_sum': 0.0,
            'current_normalized_spend': 0.0,
            'saved_to_advertising': 0.0,
        })
        bucket['advert_level_sum'] = round(bucket['advert_level_sum'] + _fullstats_spend_value(campaign), 2)

        days_rows = campaign.get('days') or campaign.get('statistics') or campaign.get('stats') or []
        if isinstance(days_rows, dict):
            days_rows = [days_rows]
        for day in days_rows:
            if not isinstance(day, dict):
                continue
            bucket['days_level_sum'] = round(bucket['days_level_sum'] + _fullstats_spend_value(day), 2)
            apps = day.get('apps') or day.get('items') or day.get('nm') or [day]
            if not isinstance(apps, list):
                apps = [day]
            for app in apps:
                app_node = app if isinstance(app, dict) else day
                bucket['apps_level_sum'] = round(bucket['apps_level_sum'] + _fullstats_spend_value(app_node), 2)
                nm_items = app_node.get('nm') or app_node.get('nms') or app_node.get('items') or [app_node]
                if not isinstance(nm_items, list):
                    nm_items = [app_node]
                for item in nm_items:
                    item_node = item if isinstance(item, dict) else app_node
                    bucket['nms_level_sum'] = round(bucket['nms_level_sum'] + _fullstats_spend_value(item_node), 2)

    for row in _iter_fullstats(payload) or []:
        campaign_id = row.get('campaign_id')
        if campaign_id in (None, ''):
            continue
        campaign_key = str(campaign_id)
        bucket = campaign_buckets.setdefault(campaign_key, {
            'advert_id': campaign_key,
            'campaign_name': str(row.get('campaign_name') or ''),
            'advert_level_sum': 0.0,
            'days_level_sum': 0.0,
            'apps_level_sum': 0.0,
            'nms_level_sum': 0.0,
            'current_normalized_spend': 0.0,
            'saved_to_advertising': 0.0,
        })
        if not bucket['campaign_name'] and row.get('campaign_name'):
            bucket['campaign_name'] = str(row.get('campaign_name') or '')
        bucket['current_normalized_spend'] = round(bucket['current_normalized_spend'] + float(_num(row.get('spend'))), 2)

    local_saved = _local_advertising_saved_by_campaign(telegram_id, begin, end)
    for campaign_key, amount in local_saved.items():
        bucket = campaign_buckets.setdefault(campaign_key, {
            'advert_id': campaign_key,
            'campaign_name': '',
            'advert_level_sum': 0.0,
            'days_level_sum': 0.0,
            'apps_level_sum': 0.0,
            'nms_level_sum': 0.0,
            'current_normalized_spend': 0.0,
            'saved_to_advertising': 0.0,
        })
        bucket['saved_to_advertising'] = round(float(amount or 0), 2)

    result['campaigns_returned'] = len(campaign_buckets)
    campaign_ids = sorted(
        set(list(campaign_buckets.keys()) + list(descriptor_map.keys())),
        key=lambda value: int(value) if str(value).isdigit() else str(value),
    )
    for campaign_key in campaign_ids:
        bucket = campaign_buckets.get(campaign_key)
        descriptor = descriptor_map.get(campaign_key) or {}
        campaign_name = ''
        if bucket:
            campaign_name = bucket.get('campaign_name') or ''
        if not campaign_name:
            campaign_name = str(descriptor.get('name') or '')
        result['campaigns'].append({
            'advert_id': campaign_key,
            'campaign_name': campaign_name,
            'advert_level_sum': round(float(bucket.get('advert_level_sum') or 0), 2) if bucket else 0.0,
            'days_level_sum': round(float(bucket.get('days_level_sum') or 0), 2) if bucket else 0.0,
            'apps_level_sum': round(float(bucket.get('apps_level_sum') or 0), 2) if bucket else 0.0,
            'nms_level_sum': round(float(bucket.get('nms_level_sum') or 0), 2) if bucket else 0.0,
            'current_normalized_spend': round(float(bucket.get('current_normalized_spend') or 0), 2) if bucket else 0.0,
            'saved_to_advertising': round(float(bucket.get('saved_to_advertising') or 0), 2) if bucket else 0.0,
            'in_fullstats': bool(bucket),
            'in_local_advertising': campaign_key in local_saved,
        })
    return result


def ads_fullstats_normalize_audit(telegram_id, token, begin, end, token_source='unknown'):
    result = {
        'status': 'SUCCESS',
        'period_begin': str(begin),
        'period_end': str(end),
        'count_status': None,
        'fullstats_status': None,
        'campaigns_found': 0,
        'campaigns_returned': 0,
        'formula': 'normalized_spend = sum(item direct spend) + aggregate app/day spend once when NM spend is absent',
        'code_path': "_iter_fullstats(): NM rows use only item.sum/item.spend/item.cost; app/day spend is emitted once as aggregate row when needed",
        'campaigns': [],
        'notes': [],
    }

    count_payload, count_status = _get(
        f'{AD_API}/adv/v1/promotion/count',
        token,
        token_source=token_source,
        caller='ads_fullstats_normalize_audit->promotion/count'
    )
    result['count_status'] = count_status
    campaign_descriptors = _extract_campaign_descriptors(count_payload)
    descriptor_map = {str(item.get('advert_id')): item for item in campaign_descriptors if item.get('advert_id') not in (None, '')}
    found_ids = [int(item['advert_id']) for item in campaign_descriptors if str(item.get('advert_id') or '').isdigit()]
    result['campaigns_found'] = len(found_ids)

    if count_status != 'SUCCESS':
        result['status'] = count_status
        result['notes'].append('promotion/count не отработал, normalizeaudit завершён только статусом вызова.')
        return result
    if not found_ids:
        result['notes'].append('promotion/count не вернул campaign_id для normalizeaudit.')
        return result

    payload, fullstats_status = _fetch_fullstats_batch(
        token,
        found_ids,
        begin,
        end,
        timeout=120,
        token_source=token_source,
    )
    result['fullstats_status'] = fullstats_status
    if fullstats_status != 'SUCCESS':
        result['status'] = fullstats_status
        result['notes'].append('fullstats не отработал, normalizeaudit недоступен.')
        return result

    campaign_buckets = {}
    for campaign in _fullstats_payload_campaigns(payload):
        if not isinstance(campaign, dict):
            continue
        campaign_id = campaign.get('advertId') or campaign.get('id') or campaign.get('campaignId')
        if campaign_id in (None, ''):
            continue
        campaign_key = str(campaign_id)
        bucket = campaign_buckets.setdefault(campaign_key, {
            'advert_id': campaign_key,
            'campaign_name': str(campaign.get('name') or campaign.get('campaignName') or ''),
            'advert_sum': round(_fullstats_spend_value(campaign), 2),
            'sum_price': 0.0,
            'normalized_spend': 0.0,
            'saved_to_advertising': 0.0,
            'step_item_sum': 0.0,
            'step_item_spend': 0.0,
            'step_item_cost': 0.0,
            'step_app_sum': 0.0,
            'step_day_sum': 0.0,
            'step_count_item_sum': 0,
            'step_count_item_spend': 0,
            'step_count_item_cost': 0,
            'step_count_app_sum': 0,
            'step_count_day_sum': 0,
            'rows_total': 0,
            'rows_with_app_sum_fallback': 0,
            'rows_with_day_sum_fallback': 0,
            'max_app_nm_count_on_fallback': 0,
        })
    for row in _iter_fullstats_trace(payload) or []:
        campaign_id = row.get('campaign_id')
        if campaign_id in (None, ''):
            continue
        campaign_key = str(campaign_id)
        bucket = campaign_buckets.setdefault(campaign_key, {
            'advert_id': campaign_key,
            'campaign_name': str(row.get('campaign_name') or ''),
            'advert_sum': 0.0,
            'sum_price': 0.0,
            'normalized_spend': 0.0,
            'saved_to_advertising': 0.0,
            'step_item_sum': 0.0,
            'step_item_spend': 0.0,
            'step_item_cost': 0.0,
            'step_app_sum': 0.0,
            'step_day_sum': 0.0,
            'step_count_item_sum': 0,
            'step_count_item_spend': 0,
            'step_count_item_cost': 0,
            'step_count_app_sum': 0,
            'step_count_day_sum': 0,
            'rows_total': 0,
            'rows_with_app_sum_fallback': 0,
            'rows_with_day_sum_fallback': 0,
            'max_app_nm_count_on_fallback': 0,
        })
        if not bucket['campaign_name'] and row.get('campaign_name'):
            bucket['campaign_name'] = str(row.get('campaign_name') or '')
        spend = round(float(_num(row.get('spend'))), 2)
        sum_price = round(float(_num(row.get('sum_price'))), 2)
        spend_source = str(row.get('spend_source') or 'none')
        bucket['rows_total'] += 1
        bucket['normalized_spend'] = round(bucket['normalized_spend'] + spend, 2)
        bucket['sum_price'] = round(bucket['sum_price'] + sum_price, 2)
        if spend_source == 'item.sum':
            bucket['step_item_sum'] = round(bucket['step_item_sum'] + spend, 2)
            bucket['step_count_item_sum'] += 1
        elif spend_source == 'item.spend':
            bucket['step_item_spend'] = round(bucket['step_item_spend'] + spend, 2)
            bucket['step_count_item_spend'] += 1
        elif spend_source == 'item.cost':
            bucket['step_item_cost'] = round(bucket['step_item_cost'] + spend, 2)
            bucket['step_count_item_cost'] += 1
        elif spend_source.startswith('app.'):
            bucket['step_app_sum'] = round(bucket['step_app_sum'] + spend, 2)
            bucket['step_count_app_sum'] += 1
            bucket['rows_with_app_sum_fallback'] += 1
            bucket['max_app_nm_count_on_fallback'] = max(bucket['max_app_nm_count_on_fallback'], int(row.get('app_nm_count') or 0))
        elif spend_source.startswith('day.'):
            bucket['step_day_sum'] = round(bucket['step_day_sum'] + spend, 2)
            bucket['step_count_day_sum'] += 1
            bucket['rows_with_day_sum_fallback'] += 1
            bucket['max_app_nm_count_on_fallback'] = max(bucket['max_app_nm_count_on_fallback'], int(row.get('app_nm_count') or 0))

    local_saved = _local_advertising_saved_by_campaign(telegram_id, begin, end)
    for campaign_key, amount in local_saved.items():
        bucket = campaign_buckets.setdefault(campaign_key, {
            'advert_id': campaign_key,
            'campaign_name': '',
            'advert_sum': 0.0,
            'sum_price': 0.0,
            'normalized_spend': 0.0,
            'saved_to_advertising': 0.0,
            'step_item_sum': 0.0,
            'step_item_spend': 0.0,
            'step_item_cost': 0.0,
            'step_app_sum': 0.0,
            'step_day_sum': 0.0,
            'step_count_item_sum': 0,
            'step_count_item_spend': 0,
            'step_count_item_cost': 0,
            'step_count_app_sum': 0,
            'step_count_day_sum': 0,
            'rows_total': 0,
            'rows_with_app_sum_fallback': 0,
            'rows_with_day_sum_fallback': 0,
            'max_app_nm_count_on_fallback': 0,
        })
        bucket['saved_to_advertising'] = round(float(amount or 0), 2)

    result['campaigns_returned'] = len(campaign_buckets)
    campaign_ids = sorted(
        set(list(campaign_buckets.keys()) + list(descriptor_map.keys())),
        key=lambda value: int(value) if str(value).isdigit() else str(value),
    )
    for campaign_key in campaign_ids:
        bucket = campaign_buckets.get(campaign_key)
        descriptor = descriptor_map.get(campaign_key) or {}
        campaign_name = (bucket.get('campaign_name') if bucket else '') or str(descriptor.get('name') or '')
        result['campaigns'].append({
            'advert_id': campaign_key,
            'campaign_name': campaign_name,
            'advert_sum': round(float(bucket.get('advert_sum') or 0), 2) if bucket else 0.0,
            'sum_price': round(float(bucket.get('sum_price') or 0), 2) if bucket else 0.0,
            'step_1_item_sum': round(float(bucket.get('step_item_sum') or 0), 2) if bucket else 0.0,
            'step_1_item_sum_count': int(bucket.get('step_count_item_sum') or 0) if bucket else 0,
            'step_2_item_spend': round(float(bucket.get('step_item_spend') or 0), 2) if bucket else 0.0,
            'step_2_item_spend_count': int(bucket.get('step_count_item_spend') or 0) if bucket else 0,
            'step_3_item_cost': round(float(bucket.get('step_item_cost') or 0), 2) if bucket else 0.0,
            'step_3_item_cost_count': int(bucket.get('step_count_item_cost') or 0) if bucket else 0,
            'step_4_app_sum': round(float(bucket.get('step_app_sum') or 0), 2) if bucket else 0.0,
            'step_4_app_sum_count': int(bucket.get('step_count_app_sum') or 0) if bucket else 0,
            'step_5_day_sum': round(float(bucket.get('step_day_sum') or 0), 2) if bucket else 0.0,
            'step_5_day_sum_count': int(bucket.get('step_count_day_sum') or 0) if bucket else 0,
            'rows_total': int(bucket.get('rows_total') or 0) if bucket else 0,
            'rows_with_app_sum_fallback': int(bucket.get('rows_with_app_sum_fallback') or 0) if bucket else 0,
            'rows_with_day_sum_fallback': int(bucket.get('rows_with_day_sum_fallback') or 0) if bucket else 0,
            'max_app_nm_count_on_fallback': int(bucket.get('max_app_nm_count_on_fallback') or 0) if bucket else 0,
            'normalized_spend': round(float(bucket.get('normalized_spend') or 0), 2) if bucket else 0.0,
            'saved_to_advertising': round(float(bucket.get('saved_to_advertising') or 0), 2) if bucket else 0.0,
            'formula_text': (
                "normalized_spend = "
                f"item.sum({round(float(bucket.get('step_item_sum') or 0), 2)}) + "
                f"item.spend({round(float(bucket.get('step_item_spend') or 0), 2)}) + "
                f"item.cost({round(float(bucket.get('step_item_cost') or 0), 2)}) + "
                f"app.sum({round(float(bucket.get('step_app_sum') or 0), 2)}) + "
                f"day.sum({round(float(bucket.get('step_day_sum') or 0), 2)})"
            ) if bucket else "normalized_spend = 0",
        })
    return result


def ads_normalize_audit(telegram_id, token, begin, end, token_source='unknown'):
    return ads_fullstats_normalize_audit(telegram_id, token, begin, end, token_source=token_source)


def _prepare_advertising_rows(cur, telegram_id, payload):
    parsed_rows = []
    spend_loaded = 0.0
    response_days_count = 0
    response_advert_ids = set()
    response_dates_by_campaign = {}
    payload_campaigns = payload.get('data') or payload.get('adverts') or payload.get('campaigns') or [] if isinstance(payload, dict) else payload if isinstance(payload, list) else []
    for campaign in payload_campaigns:
        if not isinstance(campaign, dict):
            continue
        days_rows = campaign.get('days') or campaign.get('statistics') or campaign.get('stats') or []
        if isinstance(days_rows, dict):
            days_rows = [days_rows]
        response_days_count += len([day for day in days_rows if isinstance(day, dict)])

    for r in _iter_fullstats(payload) or []:
        spend = _num(r['spend'])
        views = _int(r['views'])
        clicks = _int(r['clicks'])
        orders = _int(r['orders'])
        sum_price = _num(r['sum_price'])
        nm_id = r.get('nm_id')
        article = r.get('article') or _article_by_nm(cur, telegram_id, nm_id)
        app_type = str(r.get('app_type') or '').strip() or None
        name = str(r.get('name') or article or '').strip() or None
        ctr = clicks / views * 100 if views else 0
        cpc = spend / clicks if clicks else 0
        cr = orders / clicks * 100 if clicks else 0
        aggregate_key = r.get('aggregate_key')
        if aggregate_key:
            key = f"ad:{telegram_id}:{r['date']}:{r['campaign_id']}:{aggregate_key}"
        else:
            key = f"ad:{telegram_id}:{r['date']}:{r['campaign_id']}:{app_type or '-'}:{nm_id}:{article}"
        parsed_rows.append((key, telegram_id, r['date'], r['campaign_id'], r['campaign_name'], article, nm_id, app_type, name, views, clicks, orders, sum_price, spend, ctr, cpc, cr))
        spend_loaded += spend
        campaign_id = r.get('campaign_id')
        if campaign_id is not None:
            response_advert_ids.add(int(campaign_id))
            response_dates_by_campaign.setdefault(str(int(campaign_id)), set()).add(str(r['date'])[:10])
    parsed_rows = _aggregate_advertising_rows(parsed_rows)
    return {
        'parsed_rows': parsed_rows,
        'spend_loaded': round(spend_loaded, 2),
        'response_days_count': int(response_days_count),
        'response_advert_ids': sorted(response_advert_ids),
        'response_dates_by_campaign': response_dates_by_campaign,
    }


def _aggregate_advertising_rows(rows):
    if not rows:
        return []
    grouped = {}
    order = []
    for key, tid, advert_date, campaign_id, campaign_name, article, nm_id, app_type, name, views, clicks, orders, sum_price, spend, ctr, cpc, cr in rows:
        bucket = grouped.get(key)
        if bucket is None:
            bucket = {
                'key': key,
                'tid': tid,
                'advert_date': advert_date,
                'campaign_id': campaign_id,
                'campaign_name': campaign_name,
                'article': article,
                'nm_id': nm_id,
                'app_type': app_type,
                'name': name,
                'views': 0,
                'clicks': 0,
                'orders': 0,
                'sum_price': 0.0,
                'spend': 0.0,
            }
            grouped[key] = bucket
            order.append(key)
        bucket['views'] += int(views or 0)
        bucket['clicks'] += int(clicks or 0)
        bucket['orders'] += int(orders or 0)
        bucket['sum_price'] = round(bucket['sum_price'] + float(sum_price or 0), 2)
        bucket['spend'] = round(bucket['spend'] + float(spend or 0), 2)
        if not bucket['campaign_name'] and campaign_name:
            bucket['campaign_name'] = campaign_name
        if bucket['article'] in (None, '') and article not in (None, ''):
            bucket['article'] = article
        if bucket['nm_id'] in (None, '') and nm_id not in (None, ''):
            bucket['nm_id'] = nm_id
        if bucket['app_type'] in (None, '') and app_type not in (None, ''):
            bucket['app_type'] = app_type
        if bucket['name'] in (None, '') and name not in (None, ''):
            bucket['name'] = name

    aggregated_rows = []
    for key in order:
        bucket = grouped[key]
        views = int(bucket['views'] or 0)
        clicks = int(bucket['clicks'] or 0)
        orders = int(bucket['orders'] or 0)
        spend = round(float(bucket['spend'] or 0), 2)
        sum_price = round(float(bucket['sum_price'] or 0), 2)
        ctr = clicks / views * 100 if views else 0
        cpc = spend / clicks if clicks else 0
        cr = orders / clicks * 100 if clicks else 0
        aggregated_rows.append((
            bucket['key'],
            bucket['tid'],
            bucket['advert_date'],
            bucket['campaign_id'],
            bucket['campaign_name'],
            bucket['article'],
            bucket['nm_id'],
            bucket['app_type'],
            bucket['name'],
            views,
            clicks,
            orders,
            sum_price,
            spend,
            ctr,
            cpc,
            cr,
        ))
    return aggregated_rows


def _upsert_advertising_rows(cur, rows):
    scopes = {}
    saved = 0
    for key, tid, advert_date, campaign_id, campaign_name, article, nm_id, app_type, name, views, clicks, orders, sum_price, spend, ctr, cpc, cr in rows:
        campaign_key = str(campaign_id)
        advert_day = str(advert_date)[:10]
        scopes.setdefault(campaign_key, set()).add(advert_day)
    for campaign_key, advert_days in scopes.items():
        for advert_day in advert_days:
            cur.execute(
                '''
                DELETE FROM advertising
                WHERE telegram_id=? AND campaign_id=? AND substr(advert_date,1,10)=?
                ''',
                (rows[0][1], campaign_key, advert_day),
            )
            cur.execute(
                '''
                DELETE FROM expenses
                WHERE telegram_id=? AND source='api_advertising' AND comment=? AND substr(expense_date,1,10)=?
                ''',
                (rows[0][1], f'Campaign {campaign_key}', advert_day),
            )
    for key, tid, advert_date, campaign_id, campaign_name, article, nm_id, app_type, name, views, clicks, orders, sum_price, spend, ctr, cpc, cr in rows:
        cur.execute(
            '''
            INSERT OR REPLACE INTO advertising (
                unique_key, telegram_id, advert_date, campaign_id, campaign_name,
                supplier_article, nm_id, app_type, name, views, clicks, orders, sum_price, spend, ctr, cpc, cr
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (key, tid, advert_date, campaign_id, campaign_name, article, nm_id, app_type, name, views, clicks, orders, sum_price, spend, ctr, cpc, cr),
        )
        if spend > 0:
            _expense_insert(cur, f'adexpense:{key}', tid, advert_date, 'advertising', spend, article, f"Campaign {campaign_id}", 'api_advertising')
        saved += 1
    return saved, scopes


def _advertising_tuple_to_dict(row):
    return {
        'unique_key': row[0],
        'telegram_id': int(row[1] or 0),
        'advert_date': str(row[2]),
        'campaign_id': str(row[3]),
        'campaign_name': row[4],
        'supplier_article': row[5],
        'nm_id': row[6],
        'app_type': row[7],
        'name': row[8],
        'views': int(row[9] or 0),
        'clicks': int(row[10] or 0),
        'orders': int(row[11] or 0),
        'sum_price': round(float(row[12] or 0), 2),
        'spend': round(float(row[13] or 0), 2),
        'ctr': float(row[14] or 0),
        'cpc': float(row[15] or 0),
        'cr': float(row[16] or 0),
    }


def _advertising_dict_to_tuple(row):
    return (
        row.get('unique_key'),
        int(row.get('telegram_id') or 0),
        row.get('advert_date'),
        row.get('campaign_id'),
        row.get('campaign_name'),
        row.get('supplier_article'),
        row.get('nm_id'),
        row.get('app_type'),
        row.get('name'),
        int(row.get('views') or 0),
        int(row.get('clicks') or 0),
        int(row.get('orders') or 0),
        round(float(row.get('sum_price') or 0), 2),
        round(float(row.get('spend') or 0), 2),
        float(row.get('ctr') or 0),
        float(row.get('cpc') or 0),
        float(row.get('cr') or 0),
    )


def _advertising_signature(row):
    return (
        str(row.get('advert_date') or '')[:10],
        str(row.get('campaign_id') or ''),
        int(row.get('views') or 0),
        int(row.get('clicks') or 0),
        int(row.get('orders') or 0),
        round(float(row.get('sum_price') or 0), 2),
        round(float(row.get('spend') or 0), 2),
    )


def _advertising_rows_equal(left, right):
    fields = (
        'advert_date', 'campaign_id', 'campaign_name', 'supplier_article', 'nm_id',
        'app_type', 'name', 'views', 'clicks', 'orders', 'sum_price', 'spend',
    )
    for field in fields:
        if field in ('sum_price', 'spend'):
            if round(float(left.get(field) or 0), 2) != round(float(right.get(field) or 0), 2):
                return False
        else:
            if (left.get(field) or '') != (right.get(field) or ''):
                return False
    return True


def _advertising_match_flags(cur, telegram_id, nm_id, article):
    found_in_sales = False
    found_in_products = False
    if nm_id not in (None, ''):
        cur.execute(
            "SELECT 1 FROM sales WHERE telegram_id=? AND nm_id=? LIMIT 1",
            (telegram_id, nm_id),
        )
        found_in_sales = cur.fetchone() is not None
        cur.execute(
            "SELECT 1 FROM products WHERE telegram_id=? AND supplier_article=(SELECT supplier_article FROM sales WHERE telegram_id=? AND nm_id=? LIMIT 1) LIMIT 1",
            (telegram_id, telegram_id, nm_id),
        )
        found_in_products = cur.fetchone() is not None
    if article and not found_in_sales:
        cur.execute(
            "SELECT 1 FROM sales WHERE telegram_id=? AND TRIM(COALESCE(supplier_article,''))=? LIMIT 1",
            (telegram_id, str(article).strip()),
        )
        found_in_sales = cur.fetchone() is not None
    if article and not found_in_products:
        cur.execute(
            "SELECT 1 FROM products WHERE telegram_id=? AND TRIM(COALESCE(supplier_article,''))=? LIMIT 1",
            (telegram_id, str(article).strip()),
        )
        found_in_products = cur.fetchone() is not None
    return found_in_sales, found_in_products


def _advertising_projected_metrics(cur, telegram_id, rows):
    total_spend = 0.0
    linked_spend = 0.0
    linked_revenue = 0.0
    rows_real_nm = 0
    rows_placeholder_nm = 0
    rows_matching_sales = 0
    rows_matching_products = 0
    for row in rows or []:
        nm_id = row.get('nm_id')
        if isinstance(nm_id, str) and nm_id.strip().isdigit():
            nm_id = int(nm_id.strip())
        if isinstance(nm_id, (int, float)) and int(nm_id) > 0:
            rows_real_nm += 1
        elif isinstance(nm_id, (int, float)) and int(nm_id) <= 0:
            rows_placeholder_nm += 1
        total_spend = round(total_spend + float(row.get('spend') or 0), 2)
        found_in_sales, found_in_products = _advertising_match_flags(cur, telegram_id, nm_id, row.get('supplier_article'))
        if found_in_sales:
            rows_matching_sales += 1
        if found_in_products:
            rows_matching_products += 1
        if found_in_sales or found_in_products:
            linked_spend = round(linked_spend + float(row.get('spend') or 0), 2)
            linked_revenue = round(linked_revenue + float(row.get('sum_price') or 0), 2)
    return {
        'rows_after_filter': int(len(rows or [])),
        'rows_with_real_nmid': int(rows_real_nm),
        'rows_with_placeholder_nmid': int(rows_placeholder_nm),
        'rows_matching_sales': int(rows_matching_sales),
        'rows_matching_products': int(rows_matching_products),
        'projected_linked_spend': round(linked_spend, 2),
        'projected_linked_revenue': round(linked_revenue, 2),
        'projected_linkability': round((linked_spend / total_spend * 100) if total_spend else 0, 1),
        'total_spend': round(total_spend, 2),
    }


def _advertising_period_snapshot(telegram_id, start_date, end_date):
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT
                COUNT(*),
                SUM(CASE WHEN nm_id < 0 THEN 1 ELSE 0 END),
                SUM(CASE WHEN nm_id > 0 THEN 1 ELSE 0 END),
                SUM(CASE WHEN nm_id IS NULL THEN 1 ELSE 0 END),
                ROUND(COALESCE(SUM(spend), 0), 2),
                ROUND(COALESCE(SUM(sum_price), 0), 2),
                MIN(substr(advert_date,1,10)),
                MAX(substr(advert_date,1,10))
            FROM advertising
            WHERE telegram_id=? AND substr(advert_date,1,10) BETWEEN ? AND ?
            """,
            (telegram_id, str(start_date), str(end_date)),
        )
        row = cur.fetchone() or (0, 0, 0, 0, 0, 0, None, None)
        cur.execute(
            """
            SELECT unique_key, telegram_id, advert_date, campaign_id, campaign_name,
                   supplier_article, nm_id, app_type, name, views, clicks, orders, sum_price, spend, ctr, cpc, cr
            FROM advertising
            WHERE telegram_id=? AND substr(advert_date,1,10) BETWEEN ? AND ?
            """,
            (telegram_id, str(start_date), str(end_date)),
        )
        rows = [_advertising_tuple_to_dict(item) for item in cur.fetchall()]
        metrics = _advertising_projected_metrics(cur, telegram_id, rows)
        return {
            'rows': int(row[0] or 0),
            'rows_with_negative_nmid': int(row[1] or 0),
            'rows_with_positive_nmid': int(row[2] or 0),
            'rows_with_null_nmid': int(row[3] or 0),
            'total_spend': round(float(row[4] or 0), 2),
            'total_revenue': round(float(row[5] or 0), 2),
            'min_date': row[6],
            'max_date': row[7],
            'linked_spend': round(float(metrics.get('projected_linked_spend') or 0), 2),
            'linked_revenue': round(float(metrics.get('projected_linked_revenue') or 0), 2),
            'linkability': round(float(metrics.get('projected_linkability') or 0), 1),
        }
    finally:
        conn.close()


def _ads_cleanup_scope_key(campaign_id, advert_date):
    campaign_key = str(campaign_id or '').strip() or 'n/a'
    advert_day = str(advert_date or '')[:10]
    return campaign_key, advert_day


def _ads_cleanup_fetch_period_rows(cur, telegram_id, start_date, end_date):
    cur.execute(
        """
        SELECT id, unique_key, campaign_id, advert_date, nm_id, spend, sum_price
        FROM advertising
        WHERE telegram_id=? AND substr(advert_date,1,10) BETWEEN ? AND ?
        ORDER BY substr(advert_date,1,10), CAST(COALESCE(campaign_id, '0') AS TEXT), id
        """,
        (telegram_id, str(start_date), str(end_date)),
    )
    rows = []
    for item in cur.fetchall():
        rows.append({
            'id': int(item[0] or 0),
            'unique_key': str(item[1] or '').strip(),
            'campaign_id': str(item[2] or '').strip(),
            'advert_date': str(item[3] or '')[:10],
            'nm_id': item[4],
            'spend': round(float(item[5] or 0), 2),
            'sum_price': round(float(item[6] or 0), 2),
        })
    return rows


def _ads_cleanup_build_scope_index(rows):
    scopes = {}
    for row in rows or []:
        scope_key = _ads_cleanup_scope_key(row.get('campaign_id'), row.get('advert_date'))
        bucket = scopes.get(scope_key)
        if bucket is None:
            bucket = {
                'campaign_id': scope_key[0],
                'advert_date': scope_key[1],
                'positive_rows': 0,
                'negative_rows': 0,
                'positive_spend': 0.0,
                'negative_spend': 0.0,
                'positive_revenue': 0.0,
                'negative_revenue': 0.0,
            }
            scopes[scope_key] = bucket
        nm_id = row.get('nm_id')
        try:
            normalized_nm_id = int(str(nm_id).strip()) if nm_id not in (None, '') else None
        except Exception:
            normalized_nm_id = None
        spend = round(float(row.get('spend') or 0), 2)
        revenue = round(float(row.get('sum_price') or 0), 2)
        if normalized_nm_id is not None and normalized_nm_id > 0:
            bucket['positive_rows'] += 1
            bucket['positive_spend'] = round(bucket['positive_spend'] + spend, 2)
            bucket['positive_revenue'] = round(bucket['positive_revenue'] + revenue, 2)
        elif normalized_nm_id is not None and normalized_nm_id < 0:
            bucket['negative_rows'] += 1
            bucket['negative_spend'] = round(bucket['negative_spend'] + spend, 2)
            bucket['negative_revenue'] = round(bucket['negative_revenue'] + revenue, 2)
    return scopes


def advertising_duplicate_audit(telegram_id, start_date, end_date):
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        rows = _ads_cleanup_fetch_period_rows(cur, telegram_id, start_date, end_date)
    finally:
        conn.close()

    scopes = _ads_cleanup_build_scope_index(rows)
    positive_rows = 0
    negative_rows = 0
    spend_positive_nm_id = 0.0
    spend_negative_nm_id = 0.0
    overlap_scope_count = 0
    spend_overlap_by_campaign_date = 0.0
    estimated_duplicated_spend = 0.0
    estimated_duplicated_revenue = 0.0

    for row in rows:
        nm_id = row.get('nm_id')
        try:
            normalized_nm_id = int(str(nm_id).strip()) if nm_id not in (None, '') else None
        except Exception:
            normalized_nm_id = None
        if normalized_nm_id is not None and normalized_nm_id > 0:
            positive_rows += 1
            spend_positive_nm_id = round(spend_positive_nm_id + float(row.get('spend') or 0), 2)
        elif normalized_nm_id is not None and normalized_nm_id < 0:
            negative_rows += 1
            spend_negative_nm_id = round(spend_negative_nm_id + float(row.get('spend') or 0), 2)

    overlapping_scopes = []
    for bucket in scopes.values():
        if int(bucket.get('positive_rows') or 0) > 0 and int(bucket.get('negative_rows') or 0) > 0:
            overlap_scope_count += 1
            overlap_spend = round(min(float(bucket.get('positive_spend') or 0), float(bucket.get('negative_spend') or 0)), 2)
            spend_overlap_by_campaign_date = round(spend_overlap_by_campaign_date + overlap_spend, 2)
            estimated_duplicated_spend = round(estimated_duplicated_spend + float(bucket.get('negative_spend') or 0), 2)
            estimated_duplicated_revenue = round(estimated_duplicated_revenue + float(bucket.get('negative_revenue') or 0), 2)
            overlapping_scopes.append({
                'campaign_id': bucket.get('campaign_id') or '',
                'advert_date': bucket.get('advert_date') or '',
                'positive_rows': int(bucket.get('positive_rows') or 0),
                'negative_rows': int(bucket.get('negative_rows') or 0),
                'positive_spend': round(float(bucket.get('positive_spend') or 0), 2),
                'negative_spend': round(float(bucket.get('negative_spend') or 0), 2),
                'overlap_spend': overlap_spend,
            })

    overlapping_scopes.sort(
        key=lambda item: (-float(item.get('negative_spend') or 0), str(item.get('advert_date') or ''), str(item.get('campaign_id') or ''))
    )
    return {
        'period_begin': str(start_date),
        'period_end': str(end_date),
        'positive_nm_id_rows': int(positive_rows),
        'negative_nm_id_rows': int(negative_rows),
        'spend_positive_nm_id': round(spend_positive_nm_id, 2),
        'spend_negative_nm_id': round(spend_negative_nm_id, 2),
        'overlap_scope_count': int(overlap_scope_count),
        'spend_overlap_by_campaign_date': round(spend_overlap_by_campaign_date, 2),
        'estimated_duplicated_spend': round(estimated_duplicated_spend, 2),
        'estimated_duplicated_revenue': round(estimated_duplicated_revenue, 2),
        'overlapping_scopes': overlapping_scopes[:20],
    }


def advertising_cleanup_audit(telegram_id, start_date, end_date):
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        rows = _ads_cleanup_fetch_period_rows(cur, telegram_id, start_date, end_date)
    finally:
        conn.close()

    scopes = _ads_cleanup_build_scope_index(rows)
    negative_details = []
    negative_total_rows = 0
    negative_total_spend = 0.0
    safe_to_delete_rows = 0
    safe_to_delete_spend = 0.0
    safe_to_delete_revenue = 0.0

    for row in rows:
        nm_id = row.get('nm_id')
        try:
            normalized_nm_id = int(str(nm_id).strip()) if nm_id not in (None, '') else None
        except Exception:
            normalized_nm_id = None
        if normalized_nm_id is None or normalized_nm_id >= 0:
            continue
        negative_total_rows += 1
        spend = round(float(row.get('spend') or 0), 2)
        revenue = round(float(row.get('sum_price') or 0), 2)
        negative_total_spend = round(negative_total_spend + spend, 2)
        scope = scopes.get(_ads_cleanup_scope_key(row.get('campaign_id'), row.get('advert_date'))) or {}
        has_positive_scope = int(scope.get('positive_rows') or 0) > 0
        if has_positive_scope:
            safe_to_delete_rows += 1
            safe_to_delete_spend = round(safe_to_delete_spend + spend, 2)
            safe_to_delete_revenue = round(safe_to_delete_revenue + revenue, 2)
        negative_details.append({
            'id': int(row.get('id') or 0),
            'campaign_id': row.get('campaign_id') or '',
            'advert_date': row.get('advert_date') or '',
            'nm_id': normalized_nm_id,
            'spend': spend,
            'sum_price': revenue,
            'has_positive_version_same_campaign_date': bool(has_positive_scope),
        })

    negative_details.sort(
        key=lambda item: (
            str(item.get('advert_date') or ''),
            str(item.get('campaign_id') or ''),
            0 if item.get('has_positive_version_same_campaign_date') else 1,
            -float(item.get('spend') or 0),
            int(item.get('id') or 0),
        )
    )
    if negative_total_rows <= 0 or safe_to_delete_rows == negative_total_rows:
        verdict = 'safe_for_cleanup'
    else:
        verdict = 'legacy_rows_detected'
    return {
        'period_begin': str(start_date),
        'period_end': str(end_date),
        'negative_rows_total': int(negative_total_rows),
        'negative_spend_total': round(negative_total_spend, 2),
        'safe_to_delete_rows': int(safe_to_delete_rows),
        'safe_to_delete_spend': round(safe_to_delete_spend, 2),
        'safe_to_delete_revenue': round(safe_to_delete_revenue, 2),
        'unsafe_rows': int(max(0, negative_total_rows - safe_to_delete_rows)),
        'unsafe_spend': round(max(0.0, negative_total_spend - safe_to_delete_spend), 2),
        'verdict': verdict,
        'rows': negative_details,
    }


def cleanup_historical_advertising_rows(telegram_id, start_date, end_date):
    init_db()
    audit = advertising_cleanup_audit(telegram_id, start_date, end_date)
    db_before = _advertising_period_snapshot(telegram_id, start_date, end_date)
    candidate_rows = [row for row in (audit.get('rows') or []) if row.get('has_positive_version_same_campaign_date')]
    candidate_ids = [int(row.get('id') or 0) for row in candidate_rows if int(row.get('id') or 0) > 0]
    candidate_unique_keys = []

    result = {
        'status': 'SUCCESS',
        'period_begin': str(start_date),
        'period_end': str(end_date),
        'audit': audit,
        'db_before': db_before,
        'deleted_rows': 0,
        'deleted_spend': 0.0,
        'deleted_revenue': 0.0,
        'deleted_expenses': 0,
        'db_after': db_before,
        'write_performed': False,
    }
    if not candidate_ids:
        result['status'] = 'NOTHING_TO_DELETE'
        return result

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        placeholders = ','.join('?' for _ in candidate_ids)
        cur.execute(
            f"""
            SELECT id, unique_key, spend, sum_price
            FROM advertising
            WHERE telegram_id=? AND id IN ({placeholders}) AND nm_id < 0
            """,
            [telegram_id] + candidate_ids,
        )
        existing_candidates = cur.fetchall()
        if not existing_candidates:
            result['status'] = 'NOTHING_TO_DELETE'
            return result
        deleted_rows = 0
        deleted_spend = 0.0
        deleted_revenue = 0.0
        for item in existing_candidates:
            deleted_rows += 1
            candidate_unique_keys.append(str(item[1] or '').strip())
            deleted_spend = round(deleted_spend + float(item[2] or 0), 2)
            deleted_revenue = round(deleted_revenue + float(item[3] or 0), 2)

        cur.execute(
            f"""
            DELETE FROM advertising
            WHERE telegram_id=? AND id IN ({placeholders}) AND nm_id < 0
            """,
            [telegram_id] + candidate_ids,
        )
        deleted_advertising = int(cur.rowcount or 0)
        deleted_expenses = 0
        for unique_key in candidate_unique_keys:
            if not unique_key:
                continue
            cur.execute(
                """
                DELETE FROM expenses
                WHERE telegram_id=? AND unique_key=?
                """,
                (telegram_id, f'adexpense:{unique_key}'),
            )
            deleted_expenses += int(cur.rowcount or 0)
        conn.commit()
        result['deleted_rows'] = int(deleted_advertising)
        result['deleted_spend'] = round(deleted_spend, 2)
        result['deleted_revenue'] = round(deleted_revenue, 2)
        result['deleted_expenses'] = int(deleted_expenses)
        result['db_after'] = _advertising_period_snapshot(telegram_id, start_date, end_date)
        result['write_performed'] = True
    except Exception:
        conn.rollback()
        result['status'] = 'EXCEPTION'
    finally:
        conn.close()
    return result


def _sync_advertising_expense(cur, telegram_id, old_unique_key, row):
    spend = round(float(row.get('spend') or 0), 2)
    old_expense_key = f"adexpense:{old_unique_key}" if old_unique_key else None
    new_expense_key = f"adexpense:{row.get('unique_key')}"
    if spend > 0:
        if old_expense_key:
            cur.execute(
                """
                UPDATE expenses
                SET unique_key=?, expense_date=?, amount=?, supplier_article=?, comment=?, source='api_advertising'
                WHERE telegram_id=? AND unique_key=?
                """,
                (
                    new_expense_key,
                    row.get('advert_date'),
                    spend,
                    row.get('supplier_article'),
                    f"Campaign {row.get('campaign_id')}",
                    telegram_id,
                    old_expense_key,
                ),
            )
            if int(cur.rowcount or 0) > 0:
                return
        _expense_insert(
            cur,
            new_expense_key,
            telegram_id,
            row.get('advert_date'),
            'advertising',
            spend,
            row.get('supplier_article'),
            f"Campaign {row.get('campaign_id')}",
            'api_advertising',
        )


def _safe_upsert_historical_advertising_rows(cur, telegram_id, rows, start_date, end_date):
    cur.execute(
        """
        SELECT id, unique_key, telegram_id, advert_date, campaign_id, campaign_name,
               supplier_article, nm_id, app_type, name, views, clicks, orders, sum_price, spend, ctr, cpc, cr
        FROM advertising
        WHERE telegram_id=? AND substr(advert_date,1,10) BETWEEN ? AND ?
        """,
        (telegram_id, str(start_date), str(end_date)),
    )
    existing_rows = []
    for item in cur.fetchall():
        existing_rows.append({
            'id': int(item[0]),
            **_advertising_tuple_to_dict(item[1:]),
        })
    by_unique_key = {str(item.get('unique_key')): item for item in existing_rows if item.get('unique_key')}
    by_signature = defaultdict(list)
    for item in existing_rows:
        by_signature[_advertising_signature(item)].append(item)
    used_existing_ids = set()
    stats = {'inserted': 0, 'updated': 0, 'skipped': 0, 'invalid': 0, 'errors': 0}
    for row in rows or []:
        normalized = dict(row or {})
        normalized['telegram_id'] = int(telegram_id or 0)
        normalized['sum_price'] = round(float(normalized.get('sum_price') or 0), 2)
        normalized['spend'] = round(float(normalized.get('spend') or 0), 2)
        normalized['views'] = int(normalized.get('views') or 0)
        normalized['clicks'] = int(normalized.get('clicks') or 0)
        normalized['orders'] = int(normalized.get('orders') or 0)
        normalized['ctr'] = float(normalized.get('ctr') or 0)
        normalized['cpc'] = float(normalized.get('cpc') or 0)
        normalized['cr'] = float(normalized.get('cr') or 0)
        existing = by_unique_key.get(str(normalized.get('unique_key') or ''))
        if existing and int(existing.get('id') or 0) not in used_existing_ids:
            used_existing_ids.add(int(existing.get('id') or 0))
            if _advertising_rows_equal(existing, normalized):
                stats['skipped'] += 1
                continue
            cur.execute(
                """
                UPDATE advertising
                SET unique_key=?, advert_date=?, campaign_id=?, campaign_name=?, supplier_article=?, nm_id=?,
                    app_type=?, name=?, views=?, clicks=?, orders=?, sum_price=?, spend=?, ctr=?, cpc=?, cr=?
                WHERE id=?
                """,
                (
                    normalized.get('unique_key'),
                    normalized.get('advert_date'),
                    normalized.get('campaign_id'),
                    normalized.get('campaign_name'),
                    normalized.get('supplier_article'),
                    normalized.get('nm_id'),
                    normalized.get('app_type'),
                    normalized.get('name'),
                    normalized.get('views'),
                    normalized.get('clicks'),
                    normalized.get('orders'),
                    normalized.get('sum_price'),
                    normalized.get('spend'),
                    normalized.get('ctr'),
                    normalized.get('cpc'),
                    normalized.get('cr'),
                    existing.get('id'),
                ),
            )
            _sync_advertising_expense(cur, telegram_id, existing.get('unique_key'), normalized)
            stats['updated'] += 1
            continue
        signature_candidates = [
            item for item in by_signature.get(_advertising_signature(normalized), [])
            if int(item.get('id') or 0) not in used_existing_ids
        ]
        if len(signature_candidates) == 1:
            existing = signature_candidates[0]
            used_existing_ids.add(int(existing.get('id') or 0))
            if _advertising_rows_equal(existing, normalized):
                stats['skipped'] += 1
                continue
            cur.execute(
                """
                UPDATE advertising
                SET unique_key=?, advert_date=?, campaign_id=?, campaign_name=?, supplier_article=?, nm_id=?,
                    app_type=?, name=?, views=?, clicks=?, orders=?, sum_price=?, spend=?, ctr=?, cpc=?, cr=?
                WHERE id=?
                """,
                (
                    normalized.get('unique_key'),
                    normalized.get('advert_date'),
                    normalized.get('campaign_id'),
                    normalized.get('campaign_name'),
                    normalized.get('supplier_article'),
                    normalized.get('nm_id'),
                    normalized.get('app_type'),
                    normalized.get('name'),
                    normalized.get('views'),
                    normalized.get('clicks'),
                    normalized.get('orders'),
                    normalized.get('sum_price'),
                    normalized.get('spend'),
                    normalized.get('ctr'),
                    normalized.get('cpc'),
                    normalized.get('cr'),
                    existing.get('id'),
                ),
            )
            _sync_advertising_expense(cur, telegram_id, existing.get('unique_key'), normalized)
            stats['updated'] += 1
            continue
        if len(signature_candidates) > 1:
            stats['invalid'] += 1
            continue
        cur.execute(
            """
            INSERT INTO advertising (
                unique_key, telegram_id, advert_date, campaign_id, campaign_name,
                supplier_article, nm_id, app_type, name, views, clicks, orders, sum_price, spend, ctr, cpc, cr
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _advertising_dict_to_tuple(normalized),
        )
        _sync_advertising_expense(cur, telegram_id, None, normalized)
        stats['inserted'] += 1
    return stats


def _probe_verdict(status):
    s = str(status or '')
    if s == 'SUCCESS':
        return 'endpoint рабочий'
    if s.startswith('FULLSTATS_429:') or s.startswith('RATE_LIMIT:') or s.startswith('ADS_COOLDOWN:'):
        return 'лимит'
    if s in ('FULLSTATS_INVALID_BEGIN', 'FULLSTATS_400', 'ERROR_400', 'DISCOVERY_404', 'FULLSTATS_404'):
        return 'ошибка контракта'
    if s in ('ERROR_401', 'NO_WB_TOKEN'):
        return 'проблема токена'
    return 'ошибка'


def _sample_payload(payload, limit=400):
    if payload is None:
        return '<empty>'
    try:
        text = json.dumps(payload, ensure_ascii=False)
    except Exception:
        text = str(payload)
    return text[:limit]


def _ads_http_probe(token, url, params=None, timeout=20, token_source='unknown'):
    _log_ads_token_debug(token, token_source)
    try:
        resp = httpx.get(url, headers=_headers(token), params=params, timeout=timeout)
    except httpx.TimeoutException:
        return {'endpoint': url, 'params': params or {}, 'http_status': 'TIMEOUT', 'sample': '<timeout>', 'retry_after': None, 'status': 'TIMEOUT'}
    except Exception as exc:
        return {'endpoint': url, 'params': params or {}, 'http_status': 'CONNECTION_ERROR', 'sample': repr(exc)[:400], 'retry_after': None, 'status': 'CONNECTION_ERROR'}

    retry_after = resp.headers.get('x-ratelimit-retry') or resp.headers.get('X-Ratelimit-Retry')
    body_text = (resp.text or '')[:400]
    try:
        payload = resp.json() if resp.content else None
    except Exception:
        payload = None

    status = 'SUCCESS' if resp.status_code == 200 else f'ERROR_{resp.status_code}'
    if resp.status_code == 429:
        status = f'FULLSTATS_429:{retry_after or "unknown"}'
    elif resp.status_code == 400 and 'Invalid begin date' in (resp.text or ''):
        status = 'FULLSTATS_INVALID_BEGIN'

    return {
        'endpoint': url,
        'params': params or {},
        'http_status': resp.status_code,
        'sample': _sample_payload(payload) if payload is not None else body_text,
        'retry_after': retry_after,
        'status': status,
        'payload': payload,
        'response_text': resp.text or '',
    }


def ads_contract_probe(telegram_id, token, variant, days=1, token_source='unknown'):
    begin = _date_from(days)
    end = _today()
    url = f'{AD_API}/adv/v3/fullstats'
    variant_name = str(variant or '').strip().upper()
    variant_params = {
        'A': {'ids': None, 'begin': begin, 'end': end},
        'B': {'ids': None, 'begin': f'{begin}T00:00:00', 'end': f'{end}T23:59:59'},
        'C': {'id': None, 'begin': begin, 'end': end},
        'D': {'ids': None, 'beginDate': begin, 'endDate': end},
        'E': {'ids': None, 'begin': f'{begin}T00:00:00Z', 'end': f'{end}T23:59:59Z'},
    }
    if variant_name not in variant_params:
        return {
            'calls': [],
            'final_status': 'INVALID_VARIANT',
            'campaign_id': None,
            'variant': variant_name,
        }

    cooldown_row = get_api_cooldown(telegram_id, 'advertising') or {}
    retry_after = _parse_dt(cooldown_row.get('retry_after'))
    now_dt = _now_dt()
    if retry_after and retry_after > now_dt:
        seconds_left = int((retry_after - now_dt).total_seconds())
        _log_ads_cooldown_debug(
            status=f'ADS_COOLDOWN:{seconds_left}',
            retry_after=cooldown_row.get('retry_after'),
            saved_until=cooldown_row.get('retry_after'),
            now=now_dt.strftime('%Y-%m-%d %H:%M:%S'),
            remaining=seconds_left,
        )
        return {
            'calls': [],
            'final_status': f'ADS_COOLDOWN:{seconds_left}',
            'campaign_id': None,
            'variant': variant_name,
            'retry_after': cooldown_row.get('retry_after'),
            'seconds_left': seconds_left,
        }

    count_call = _ads_http_probe(token, f'{AD_API}/adv/v1/promotion/count', params=None, timeout=20, token_source=token_source)
    result = {
        'calls': [count_call],
        'final_status': count_call['status'],
        'campaign_id': None,
        'variant': variant_name,
    }
    if count_call['status'] != 'SUCCESS':
        return result

    ids = _collect_ad_ids(count_call.get('payload'))
    if not ids:
        result['final_status'] = 'NO_CAMPAIGNS'
        result['note'] = 'Кампании не найдены, fullstats не проверялся.'
        return result

    campaign_id = str(int(ids[0]))
    result['campaign_id'] = int(campaign_id)
    params = dict(variant_params[variant_name])
    if 'ids' in params:
        params['ids'] = campaign_id
    if 'id' in params:
        params['id'] = campaign_id

    call = _ads_http_probe(token, url, params=params, timeout=20, token_source=token_source)
    call['variant'] = variant_name
    call['sample'] = str(call.get('sample') or '<empty>')[:500]
    result['calls'].append(call)
    result['final_status'] = call['status']

    return result


def ads_probe(token, days=1, token_source='unknown'):
    begin = _date_from(days)
    end = _today()

    count_call = _ads_http_probe(token, f'{AD_API}/adv/v1/promotion/count', params=None, timeout=20, token_source=token_source)
    result = {
        'calls': [count_call],
        'final_status': count_call['status'],
        'verdict': _probe_verdict(count_call['status']),
    }
    if count_call['status'] != 'SUCCESS':
        return result

    ids = _collect_ad_ids(count_call.get('payload'))
    if not ids:
        result['final_status'] = 'SUCCESS'
        result['verdict'] = 'endpoint рабочий'
        result['note'] = 'Кампании не найдены, fullstats не проверялся.'
        return result

    fullstats_call = _ads_http_probe(
        token,
        f'{AD_API}/adv/v3/fullstats',
        params={'ids': str(int(ids[0])), 'beginDate': begin, 'endDate': end},
        timeout=20,
        token_source=token_source,
    )
    result['calls'].append(fullstats_call)
    result['final_status'] = fullstats_call['status']
    result['verdict'] = _probe_verdict(fullstats_call['status'])
    result['campaign_id'] = int(ids[0])
    return result


def ads_limit_test(token, max_requests=10, token_source='unknown'):
    test_date = _prev_date(_today())
    count_call = _ads_http_probe(token, f'{AD_API}/adv/v1/promotion/count', params=None, timeout=20, token_source=token_source)
    result = {
        'date': test_date,
        'max_requests': int(max_requests or 10),
        'count_call': count_call,
        'requests_done': 0,
        'status_200': 0,
        'status_400': 0,
        'first_429_request': None,
        'calls': [],
        'campaign_ids': [],
        'recommendation': '',
    }
    if count_call.get('status') != 'SUCCESS':
        result['recommendation'] = 'Не удалось получить campaign_id через promotion/count.'
        return result

    ids = [int(x) for x in _collect_ad_ids(count_call.get('payload')) if x is not None]
    result['campaign_ids'] = ids
    if not ids:
        result['recommendation'] = 'Кампании не найдены, лимит fullstats не проверялся.'
        return result

    endpoint = f'{AD_API}/adv/v3/fullstats'
    for idx, campaign_id in enumerate(ids[:result['max_requests']], start=1):
        _log_ads_token_debug(token, token_source)
        try:
            resp = httpx.get(
                endpoint,
                headers=_headers(token),
                params={'ids': str(campaign_id), 'beginDate': test_date, 'endDate': test_date},
                timeout=20,
            )
            body = resp.text or ''
            call = {
                'request_number': idx,
                'campaign_id': campaign_id,
                'endpoint': endpoint,
                'params': {'ids': str(campaign_id), 'beginDate': test_date, 'endDate': test_date},
                'http_status': resp.status_code,
                'sample': body[:300] or '<empty>',
                'x_ratelimit_limit': resp.headers.get('x-ratelimit-limit') or resp.headers.get('X-Ratelimit-Limit'),
                'x_ratelimit_retry': resp.headers.get('x-ratelimit-retry') or resp.headers.get('X-Ratelimit-Retry'),
                'x_ratelimit_reset': resp.headers.get('x-ratelimit-reset') or resp.headers.get('X-Ratelimit-Reset'),
            }
        except httpx.TimeoutException:
            call = {
                'request_number': idx,
                'campaign_id': campaign_id,
                'endpoint': endpoint,
                'params': {'ids': str(campaign_id), 'beginDate': test_date, 'endDate': test_date},
                'http_status': 'TIMEOUT',
                'sample': '<timeout>',
                'x_ratelimit_limit': None,
                'x_ratelimit_retry': None,
                'x_ratelimit_reset': None,
            }
        except Exception as exc:
            call = {
                'request_number': idx,
                'campaign_id': campaign_id,
                'endpoint': endpoint,
                'params': {'ids': str(campaign_id), 'beginDate': test_date, 'endDate': test_date},
                'http_status': 'CONNECTION_ERROR',
                'sample': repr(exc)[:300],
                'x_ratelimit_limit': None,
                'x_ratelimit_retry': None,
                'x_ratelimit_reset': None,
            }

        result['calls'].append(call)
        result['requests_done'] = idx
        if call['http_status'] == 200:
            result['status_200'] += 1
        elif call['http_status'] == 400:
            result['status_400'] += 1
        elif call['http_status'] == 429:
            result['first_429_request'] = idx
            break

        if idx < min(len(ids), result['max_requests']):
            sleep(5)

    if result['first_429_request'] == 1:
        result['recommendation'] = '429 пришёл на первом запросе: лимит жёсткий, боевую загрузку лучше оставлять только по одному шагу.'
    elif result['status_200'] >= 5:
        result['recommendation'] = 'Удалось пройти 5+ успешных запросов: можно рассматривать осторожное расширение боевой загрузки.'
    elif result['status_200'] >= 1:
        result['recommendation'] = 'Есть успешные запросы, но запас лимита небольшой: пока безопаснее грузить только по одному шагу.'
    else:
        result['recommendation'] = 'Надёжного запаса лимита не видно: лучше не расширять боевую загрузку.'
    return result


def ads_batch_test(token, batch_size=3, token_source='unknown'):
    test_date = _prev_date(_today())
    count_call = _ads_http_probe(token, f'{AD_API}/adv/v1/promotion/count', params=None, timeout=20, token_source=token_source)
    result = {
        'date': test_date,
        'batch_size': max(1, int(batch_size or 3)),
        'count_call': count_call,
        'campaign_ids': [],
        'request': None,
        'http_status': None,
        'response_first_300': '<empty>',
        'returned_objects': 0,
        'total_spend': 0.0,
        'advert_ids': [],
        'x_ratelimit_limit': None,
        'x_ratelimit_retry': None,
        'x_ratelimit_reset': None,
        'verdict': '',
    }
    if count_call.get('status') != 'SUCCESS':
        result['verdict'] = 'Не удалось получить campaign_id через promotion/count.'
        return result

    ids = [int(x) for x in _collect_ad_ids(count_call.get('payload')) if x is not None]
    result['campaign_ids'] = ids[:result['batch_size']]
    if not result['campaign_ids']:
        result['verdict'] = 'Кампании не найдены, batch fullstats не проверялся.'
        return result

    endpoint = f'{AD_API}/adv/v3/fullstats'
    params = {
        'ids': ','.join(str(x) for x in result['campaign_ids']),
        'beginDate': test_date,
        'endDate': test_date,
    }
    result['request'] = {
        'endpoint': endpoint,
        'params': params,
    }
    _log_ads_token_debug(token, token_source)
    try:
        resp = httpx.get(endpoint, headers=_headers(token), params=params, timeout=20)
        result['http_status'] = resp.status_code
        result['response_first_300'] = (resp.text or '')[:300] or '<empty>'
        result['x_ratelimit_limit'] = resp.headers.get('x-ratelimit-limit') or resp.headers.get('X-Ratelimit-Limit')
        result['x_ratelimit_retry'] = resp.headers.get('x-ratelimit-retry') or resp.headers.get('X-Ratelimit-Retry')
        result['x_ratelimit_reset'] = resp.headers.get('x-ratelimit-reset') or resp.headers.get('X-Ratelimit-Reset')
        if resp.status_code == 200:
            try:
                payload = resp.json()
            except Exception:
                payload = None
            rows = list(_iter_fullstats(payload) or [])
            result['returned_objects'] = len(rows)
            result['total_spend'] = round(sum(_num(row.get('spend')) for row in rows), 2)
            advert_ids = []
            for row in rows:
                advert_id = row.get('campaign_id')
                if advert_id is not None and advert_id not in advert_ids:
                    advert_ids.append(advert_id)
            result['advert_ids'] = advert_ids[:10]
            result['verdict'] = 'batch ids работает'
        elif resp.status_code == 400:
            result['verdict'] = 'HTTP 400: возможно ids не принимает список.'
        elif resp.status_code == 429:
            result['verdict'] = 'HTTP 429: упёрлись в лимит WB Advertising API.'
        else:
            result['verdict'] = f'HTTP {resp.status_code}: контракт требует дополнительной проверки.'
    except httpx.TimeoutException:
        result['http_status'] = 'TIMEOUT'
        result['response_first_300'] = '<timeout>'
        result['verdict'] = 'Timeout при batch-запросе.'
    except Exception as exc:
        result['http_status'] = 'CONNECTION_ERROR'
        result['response_first_300'] = repr(exc)[:300]
        result['verdict'] = 'Ошибка соединения при batch-запросе.'
    return result


def ads_period_test(token, days=30, token_source='unknown'):
    end_date = _today()
    begin_date = _date_from(days)
    count_call = _ads_http_probe(token, f'{AD_API}/adv/v1/promotion/count', params=None, timeout=20, token_source=token_source)
    result = {
        'begin_date': begin_date,
        'end_date': end_date,
        'count_call': count_call,
        'campaign_ids_sent': 0,
        'http_status': None,
        'returned_advert_ids_count': 0,
        'total_days_count': 0,
        'total_spend': 0.0,
        'first_3_advert_ids': [],
        'first_5_dates': [],
        'response_size_chars': 0,
        'response_first_500': '<empty>',
        'x_ratelimit_limit': None,
        'x_ratelimit_retry': None,
        'x_ratelimit_reset': None,
        'verdict': '',
    }
    if count_call.get('status') != 'SUCCESS':
        result['verdict'] = 'Не удалось получить campaign_id через promotion/count.'
        return result

    campaign_ids = [int(x) for x in _collect_ad_ids(count_call.get('payload')) if x is not None]
    result['campaign_ids_sent'] = len(campaign_ids)
    if not campaign_ids:
        result['verdict'] = 'Кампании не найдены, fullstats не проверялся.'
        return result

    endpoint = f'{AD_API}/adv/v3/fullstats'
    params = {
        'ids': ','.join(str(x) for x in campaign_ids),
        'beginDate': begin_date,
        'endDate': end_date,
    }
    _log_ads_token_debug(token, token_source)
    try:
        resp = httpx.get(endpoint, headers=_headers(token), params=params, timeout=60)
        response_text = resp.text or ''
        result['http_status'] = resp.status_code
        result['response_size_chars'] = len(response_text)
        result['response_first_500'] = response_text[:500] or '<empty>'
        result['x_ratelimit_limit'] = resp.headers.get('x-ratelimit-limit') or resp.headers.get('X-Ratelimit-Limit')
        result['x_ratelimit_retry'] = resp.headers.get('x-ratelimit-retry') or resp.headers.get('X-Ratelimit-Retry')
        result['x_ratelimit_reset'] = resp.headers.get('x-ratelimit-reset') or resp.headers.get('X-Ratelimit-Reset')
        if resp.status_code == 200:
            try:
                payload = resp.json()
            except Exception:
                payload = None
            rows = list(_iter_fullstats(payload) or [])
            advert_ids = []
            response_dates = []
            total_days_count = 0
            if isinstance(payload, dict):
                campaigns = payload.get('data') or payload.get('adverts') or payload.get('campaigns') or []
            else:
                campaigns = payload if isinstance(payload, list) else []
            for campaign in campaigns:
                if not isinstance(campaign, dict):
                    continue
                advert_id = campaign.get('advertId') or campaign.get('id') or campaign.get('campaignId')
                if advert_id is not None and advert_id not in advert_ids:
                    advert_ids.append(advert_id)
                days_rows = campaign.get('days') or campaign.get('statistics') or campaign.get('stats') or []
                if isinstance(days_rows, dict):
                    days_rows = [days_rows]
                total_days_count += len([day for day in days_rows if isinstance(day, dict)])
                for day in days_rows:
                    if not isinstance(day, dict):
                        continue
                    day_value = str(day.get('date') or day.get('day') or '')[:10]
                    if day_value and day_value not in response_dates:
                        response_dates.append(day_value)
            if not response_dates:
                for row in rows:
                    day_value = str(row.get('date') or '')[:10]
                    if day_value and day_value not in response_dates:
                        response_dates.append(day_value)
            result['returned_advert_ids_count'] = len(advert_ids)
            result['total_days_count'] = total_days_count
            result['total_spend'] = round(sum(_num(row.get('spend')) for row in rows), 2)
            result['first_3_advert_ids'] = advert_ids[:3]
            result['first_5_dates'] = response_dates[:5]
            result['verdict'] = 'PERIOD BATCH WORKS - можно переводить боевую рекламу на весь период за 1 запрос.'
        elif resp.status_code == 400:
            result['verdict'] = 'Период слишком большой или формат не поддержан.'
        elif resp.status_code == 429:
            result['verdict'] = 'Лимит WB Advertising API.'
        else:
            result['verdict'] = f'HTTP {resp.status_code}: требуется дополнительная проверка.'
    except httpx.TimeoutException:
        result['http_status'] = 'TIMEOUT'
        result['response_first_500'] = '<timeout>'
        result['verdict'] = 'Timeout при periodtest-запросе.'
    except Exception as exc:
        result['http_status'] = 'CONNECTION_ERROR'
        result['response_first_500'] = repr(exc)[:500]
        result['verdict'] = 'Ошибка соединения при periodtest-запросе.'
    return result


def _fetch_fullstats_batch(token, batch_ids, begin, end, timeout=120, token_source='unknown'):
    try:
        ids_csv = ','.join(str(int(x)) for x in batch_ids if x is not None)
        if not ids_csv:
            return [], 'SUCCESS'
        url = f'{AD_API}/adv/v3/fullstats'
        params = {
            'ids': ids_csv,
            'beginDate': begin,
            'endDate': end,
        }
        print(f'ADS REQUEST fullstats campaign_ids_count={len([x for x in batch_ids if x is not None])}')
        try:
            resp = httpx.get(url, headers=_headers(token), params=params, timeout=timeout)
        except httpx.TimeoutException as e:
            return None, 'TIMEOUT'
        except Exception as e:
            return None, 'CONNECTION_ERROR'

        response_text = resp.text or ''
        if resp.status_code == 429:
            return None, f"FULLSTATS_429_SAFE_COOLDOWN:{_fullstats_safe_cooldown_seconds(resp)}"
        if resp.status_code == 400 and 'Invalid begin date' in response_text:
            return None, 'FULLSTATS_INVALID_BEGIN'
        if resp.status_code != 200:
            status = f'ERROR_{resp.status_code}'
            if status == 'ERROR_404':
                return None, 'FULLSTATS_404'
            if status == 'ERROR_400':
                return None, 'FULLSTATS_400'
            if status == 'ERROR_405':
                return None, 'FULLSTATS_405'
            return None, status

        try:
            payload = resp.json()
        except Exception:
            return None, 'INVALID_JSON'
        return payload, 'SUCCESS'
    except Exception as exc:
        _log_ads_exception(exc)
        raise


def inspect_fullstats_contract(batch_ids, begin, end):
    normalized_ids = [int(x) for x in batch_ids if x is not None]
    ids_csv = ','.join(str(x) for x in normalized_ids)
    get_params_variants = [
        {'ids': ids_csv, 'begin': begin, 'end': end},
        {'ids': ids_csv, 'begin': f'{begin}T00:00:00', 'end': f'{end}T23:59:59'},
        {'id': ids_csv, 'begin': begin, 'end': end},
        {'ids': ids_csv, 'beginDate': begin, 'endDate': end},
    ]
    post_payload = [{
        'id': normalized_ids[0],
        'dates': [begin],
    }] if normalized_ids else []
    return {
        'current_contract': {
            'method': 'GET',
            'endpoint': f'{AD_API}/adv/v3/fullstats',
            'query_variants': [
                {'ids': ids_csv, 'dateFrom': begin, 'dateTo': end},
                *get_params_variants,
            ],
            'payload_structure': 'GET body is not used',
        },
        'alternative_contract': {
            'method': 'POST',
            'endpoint': f'{AD_API}/adv/v3/fullstats',
            'query_params': None,
            'payload_structure': [
                {
                    'id': '<campaign_id>',
                    'dates': ['YYYY-MM-DD'],
                }
            ],
            'payload_sample': post_payload,
        },
    }


def _iter_fullstats(payload):
    yield from _iter_fullstats_rows(payload, include_trace=False)


def _legacy_load_advertising_v1(telegram_id, token, days=30):
    begin = _date_from(days)
    end = _today()
    ids, status = _fetch_advert_ids(token)
    if status != 'SUCCESS':
        return 0, status
    if not ids:
        return 0, 'SUCCESS'

    body_interval = [{'id': int(i), 'interval': {'begin': begin, 'end': end}} for i in ids[:100]]
    payload, status = _post(f'{AD_API}/adv/v2/fullstats', token, body_interval, timeout=120)
    if status != 'SUCCESS':
        # резервный формат для старых кабинетов/версий API
        body_dates = [{'id': int(i), 'dates': [begin, end]} for i in ids[:100]]
        payload, status = _post(f'{AD_API}/adv/v2/fullstats', token, body_dates, timeout=120)
        if status != 'SUCCESS':
            return 0, status

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    parsed_rows = []

    saved = 0
    for r in _iter_fullstats(payload) or []:
        spend = _num(r['spend'])
        views = _int(r['views'])
        clicks = _int(r['clicks'])
        orders = _int(r['orders'])
        sum_price = _num(r['sum_price'])
        nm_id = r.get('nm_id')
        article = r.get('article') or _article_by_nm(cur, telegram_id, nm_id)
        ctr = clicks / views * 100 if views else 0
        cpc = spend / clicks if clicks else 0
        cr = orders / clicks * 100 if clicks else 0
        key = f"ad:{telegram_id}:{r['date']}:{r['campaign_id']}:{nm_id}:{article}"
        cur.execute('''
        INSERT OR REPLACE INTO advertising (
            unique_key, telegram_id, advert_date, campaign_id, campaign_name,
            supplier_article, nm_id, views, clicks, orders, sum_price, spend, ctr, cpc, cr
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (key, telegram_id, r['date'], r['campaign_id'], r['campaign_name'], article, nm_id, views, clicks, orders, sum_price, spend, ctr, cpc, cr))
        if spend > 0:
            _expense_insert(cur, f'adexpense:{key}', telegram_id, r['date'], 'advertising', spend, article, f"Campaign {r['campaign_id']}", 'api_advertising')
        saved += 1

    conn.commit()
    conn.close()
    return saved, 'SUCCESS'


def _legacy_load_advertising_v2(telegram_id, token, days=30):
    begin = _date_from(days)
    end = _today()
    ids, status = _fetch_advert_ids(token)
    if status != 'SUCCESS':
        return 0, status
    if not ids:
        return 0, 'SUCCESS'

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    parsed_rows = []

    for i in range(0, len(ids), 100):
        batch_ids = ids[i:i + 100]
        body_interval = [{'id': int(x), 'interval': {'begin': begin, 'end': end}} for x in batch_ids]
        payload, batch_status = _post(f'{AD_API}/adv/v2/fullstats', token, body_interval, timeout=120)
        if batch_status != 'SUCCESS':
            body_dates = [{'id': int(x), 'dates': [begin, end]} for x in batch_ids]
            payload, batch_status = _post(f'{AD_API}/adv/v2/fullstats', token, body_dates, timeout=120)
            if batch_status != 'SUCCESS':
                conn.close()
                return 0, batch_status

        for r in _iter_fullstats(payload) or []:
            spend = _num(r['spend'])
            views = _int(r['views'])
            clicks = _int(r['clicks'])
            orders = _int(r['orders'])
            sum_price = _num(r['sum_price'])
            nm_id = r.get('nm_id')
            article = r.get('article') or _article_by_nm(cur, telegram_id, nm_id)
            ctr = clicks / views * 100 if views else 0
            cpc = spend / clicks if clicks else 0
            cr = orders / clicks * 100 if clicks else 0
            key = f"ad:{telegram_id}:{r['date']}:{r['campaign_id']}:{nm_id}:{article}"
            parsed_rows.append((key, telegram_id, r['date'], r['campaign_id'], r['campaign_name'], article, nm_id, views, clicks, orders, sum_price, spend, ctr, cpc, cr))

    cur.execute('DELETE FROM advertising WHERE telegram_id=? AND substr(advert_date,1,10)>=?', (telegram_id, begin))
    cur.execute('''
    DELETE FROM expenses
    WHERE telegram_id=? AND source='api_advertising' AND substr(expense_date,1,10)>=?
    ''', (telegram_id, begin))

    saved = 0
    for key, tid, advert_date, campaign_id, campaign_name, article, nm_id, views, clicks, orders, sum_price, spend, ctr, cpc, cr in parsed_rows:
        cur.execute('''
        INSERT OR REPLACE INTO advertising (
            unique_key, telegram_id, advert_date, campaign_id, campaign_name,
            supplier_article, nm_id, views, clicks, orders, sum_price, spend, ctr, cpc, cr
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (key, tid, advert_date, campaign_id, campaign_name, article, nm_id, views, clicks, orders, sum_price, spend, ctr, cpc, cr))
        if spend > 0:
            _expense_insert(cur, f'adexpense:{key}', tid, advert_date, 'advertising', spend, article, f"Campaign {campaign_id}", 'api_advertising')
        saved += 1

    conn.commit()
    conn.close()
    return saved, 'SUCCESS'


def _legacy_load_sales_for_user_v1(telegram_id=None, wb_token=None, days=30, verbose=True, load_expenses=True):
    init_db()
    token = wb_token or WB_TOKEN
    token_source = 'function_arg.wb_token' if wb_token else 'config.WB_TOKEN'
    if not token:
        save_update('NO_WB_TOKEN', 0, telegram_id)
        return 0, 'NO_WB_TOKEN'

    telegram_id = telegram_id or 0
    sales_n, sales_status = _safe_call(load_sales, telegram_id, token, days)
    orders_n, orders_status = _safe_call(load_orders, telegram_id, token, days)
    stocks_n, stocks_status = _safe_call(load_stocks, telegram_id, token)

    expenses_n = 0
    ads_n = 0
    finance_status = 'SKIPPED'
    ads_status = 'SKIPPED'
    if load_expenses:
        expenses_n, finance_status = _safe_call(load_finance_expenses, telegram_id, token, days)
        ads_n, ads_status = _safe_call(load_advertising, telegram_id, token, days)

    status = _build_update_status({
        'sales': {'status': sales_status, 'loaded': sales_n},
        'orders': {'status': orders_status, 'loaded': orders_n},
        'stocks': {'status': stocks_status, 'loaded': stocks_n},
        'finance': {'status': finance_status, 'loaded': expenses_n},
        'advertising': {'status': ads_status, 'loaded': ads_n},
    })
    save_update(format_update_status(status), sales_n, telegram_id, orders_n, expenses_n, ads_n, stocks_n)
    return sales_n, status


def get_api_status(telegram_id):
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT api_block,retry_after,last_status,updated_at FROM api_cooldowns WHERE telegram_id=? ORDER BY api_block', (telegram_id,))
    rows = cur.fetchall()
    conn.close()
    return [{'api_block': r[0], 'retry_after': r[1], 'last_status': r[2], 'updated_at': r[3]} for r in rows]


def get_last_advertising_update(telegram_id):
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT MAX(updated_at) FROM api_cooldowns WHERE telegram_id=? AND api_block='advertising' AND last_status='SUCCESS'", (telegram_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row and row[0] else None


def update_sync_status(telegram_id, sync_block, status):
    init_db()
    now = _now_str()
    last_success = now if status == 'SUCCESS' else None
    last_error = None if status == 'SUCCESS' else str(status)
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
    INSERT INTO sync_status(telegram_id,sync_block,last_success,last_error,last_status,updated_at)
    VALUES(?,?,?,?,?,?)
    ON CONFLICT(telegram_id,sync_block) DO UPDATE SET
        last_success=CASE
            WHEN excluded.last_success IS NOT NULL THEN excluded.last_success
            ELSE sync_status.last_success
        END,
        last_error=excluded.last_error,
        last_status=excluded.last_status,
        updated_at=excluded.updated_at
    ''', (telegram_id, sync_block, last_success, last_error, status, now))
    conn.commit()
    conn.close()


def get_sync_status(telegram_id):
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
    SELECT sync_block,last_success,last_error,last_status,updated_at
    FROM sync_status
    WHERE telegram_id=?
    ORDER BY sync_block
    ''', (telegram_id,))
    rows = cur.fetchall()
    conn.close()
    return [
        {
            'sync_block': r[0],
            'last_success': r[1],
            'last_error': r[2],
            'last_status': r[3],
            'updated_at': r[4],
        }
        for r in rows
    ]


def get_sync_status_map(telegram_id):
    return {row['sync_block']: row for row in get_sync_status(telegram_id)}


def get_last_sync_success(telegram_id, sync_block):
    row = get_sync_status_map(telegram_id).get(sync_block) or {}
    return row.get('last_success')


def ensure_sync_status_rows(telegram_id):
    try:
        init_db()
        now = _now_str()
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        for block in ('sales', 'orders', 'stocks', 'finance', 'advertising'):
            cur.execute('''
            INSERT OR IGNORE INTO sync_status(
                telegram_id,sync_block,last_success,last_error,last_status,updated_at
            ) VALUES(?,?,?,?,?,?)
            ''', (telegram_id, block, None, None, 'PENDING', now))
        conn.commit()
        conn.close()
    except sqlite3.OperationalError as exc:
        if _is_readonly_db_error(exc):
            return
        raise


def _update_payload(block, loaded):
    payload = {'sales_loaded': 0, 'orders_loaded': 0, 'expenses_loaded': 0, 'ads_loaded': 0, 'stocks_loaded': 0}
    if block == 'sales':
        payload['sales_loaded'] = loaded
    elif block == 'orders':
        payload['orders_loaded'] = loaded
    elif block == 'stocks':
        payload['stocks_loaded'] = loaded
    elif block == 'finance':
        payload['expenses_loaded'] = loaded
    elif block == 'advertising':
        payload['ads_loaded'] = loaded
    return payload


def sync_block_for_user(telegram_id=None, wb_token=None, block='sales', days=30, save_update_row=True):
    init_db()
    token = wb_token or WB_TOKEN
    token_source = 'function_arg.wb_token' if wb_token else 'config.WB_TOKEN'
    telegram_id = telegram_id or 0
    if not token:
        update_sync_status(telegram_id, block, 'NO_WB_TOKEN')
        if save_update_row:
            status = _build_update_status({block: {'status': 'NO_WB_TOKEN', 'loaded': 0}})
            payload = _update_payload(block, 0)
            save_update(format_update_status(status), payload['sales_loaded'], telegram_id, payload['orders_loaded'], payload['expenses_loaded'], payload['ads_loaded'], payload['stocks_loaded'])
        return 0, 'NO_WB_TOKEN'
    if block == 'advertising':
        advertising_cooldown = _cooldown_status(telegram_id, 'advertising')
        if advertising_cooldown:
            print('ADS COOLDOWN EARLY EXIT')
            print('caller=', 'sync_block_for_user')
            print('status=', advertising_cooldown)
            return 0, advertising_cooldown
        background_state = _get_ads_background_state(telegram_id)
        now_dt = _now_dt()
        blocked_until = _parse_dt(background_state.get('blocked_until'))
        if blocked_until and blocked_until > now_dt:
            seconds_left = int((blocked_until - now_dt).total_seconds())
            status = f'ADS_BACKGROUND_THROTTLED:{seconds_left}'
            print('ADS BACKGROUND THROTTLE')
            print('caller=', 'sync_block_for_user')
            print('status=', status)
            return 0, status
        last_run_at = _parse_dt(background_state.get('last_run_at'))
        if last_run_at:
            seconds_since = int((now_dt - last_run_at).total_seconds())
            min_interval = 90 * 60
            if seconds_since < min_interval:
                status = f'ADS_BACKGROUND_THROTTLED:{min_interval - seconds_since}'
                print('ADS BACKGROUND THROTTLE')
                print('caller=', 'sync_block_for_user')
                print('status=', status)
                return 0, status

    runners = {
        'sales': lambda: _run_block(telegram_id, 'sales', load_sales, telegram_id, token, days),
        'orders': lambda: _run_block(telegram_id, 'orders', load_orders, telegram_id, token, days),
        'stocks': lambda: _run_block(telegram_id, 'stocks', load_stocks, telegram_id, token),
        'finance': lambda: _run_block(telegram_id, 'finance', load_finance_expenses, telegram_id, token, days),
        'advertising': lambda: _run_block(telegram_id, 'advertising', load_advertising, telegram_id, token, days, token_source=token_source, cooldown_caller='sync_block_for_user->load_advertising'),
    }
    if block not in runners:
        update_sync_status(telegram_id, block, 'UNKNOWN_BLOCK')
        return 0, 'UNKNOWN_BLOCK'

    loaded, status = runners[block]()
    if block == 'advertising':
        background_state = _get_ads_background_state(telegram_id)
        now_dt = _now_dt()
        background_state['last_run_at'] = now_dt.strftime('%Y-%m-%d %H:%M:%S')
        if str(status).startswith('ERROR_401'):
            background_state['blocked_until'] = (now_dt + timedelta(hours=6)).strftime('%Y-%m-%d %H:%M:%S')
        else:
            background_state['blocked_until'] = None
        _set_ads_background_state(telegram_id, background_state)
    update_sync_status(telegram_id, block, status)
    if save_update_row:
        status_obj = _build_update_status({block: {'status': status, 'loaded': loaded}})
        payload = _update_payload(block, loaded)
        save_update(format_update_status(status_obj), payload['sales_loaded'], telegram_id, payload['orders_loaded'], payload['expenses_loaded'], payload['ads_loaded'], payload['stocks_loaded'])
    return loaded, status


def _load_advertising_range(telegram_id, token, days=30, token_source='unknown', allow_cooldown=True):
    conn = None
    try:
        init_db()
        if allow_cooldown:
            advertising_cooldown = _cooldown_status(telegram_id, 'advertising')
            if advertising_cooldown:
                print('ADS COOLDOWN EARLY EXIT')
                print('caller=', '_load_advertising_range')
                print('status=', advertising_cooldown)
                print(f'ADS RESULT status={advertising_cooldown} loaded=0')
                return 0, advertising_cooldown
        begin, end = _normalize_period_dates(days)
        _clear_ads_progress(telegram_id)
        fetched_ids, status = _fetch_advert_ids(token, token_source=token_source)
        known_ids = _get_known_advert_ids(telegram_id)
        batch_ids = _merge_advert_id_sources(fetched_ids, known_ids)
        _remember_known_advert_ids(telegram_id, batch_ids)
        if status != 'SUCCESS':
            _set_last_ads_run_details(telegram_id, {
                'status': status,
                'loaded': 0,
                'period_begin': begin,
                'period_end': end,
                'known_campaigns': len(known_ids),
            })
            print(f'ADS RESULT status={status} loaded=0')
            return 0, status
        if not batch_ids:
            _set_last_ads_run_details(telegram_id, {
                'status': 'SUCCESS',
                'loaded': 0,
                'total_campaigns': 0,
                'campaigns_sent': 0,
                'campaigns_found': len(fetched_ids),
                'known_campaigns': len(known_ids),
                'period_begin': begin,
                'period_end': end,
                'days_received': 0,
                'spend_loaded': 0.0,
                'api_cooldown_status': f'ADS_STEP_COOLDOWN:{ADS_SAFE_MIN_COOLDOWN_SECONDS}',
                'next_safe_seconds': ADS_SAFE_MIN_COOLDOWN_SECONDS,
            })
            print('ADS RESULT status=SUCCESS loaded=0')
            return 0, 'SUCCESS'

        total_campaigns = len(batch_ids)

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()

        payload, batch_status = _fetch_fullstats_batch(token, batch_ids, begin, end, timeout=120, token_source=token_source)
        if batch_status != 'SUCCESS':
            if batch_status == 'FULLSTATS_400':
                batch_status = 'ADS_PERIOD_BATCH_FAILED'
            api_cooldown_status = None
            if str(batch_status).startswith('FULLSTATS_429_SAFE_COOLDOWN:'):
                api_cooldown_status = batch_status
            elif batch_status in ('FULLSTATS_INVALID_BEGIN', 'ADS_PERIOD_BATCH_FAILED'):
                api_cooldown_status = f'ADS_STEP_COOLDOWN:{ADS_SAFE_MIN_COOLDOWN_SECONDS}'
            conn.close()
            conn = None
            _set_last_ads_run_details(telegram_id, {
                'status': batch_status,
                'loaded': 0,
                'total_campaigns': total_campaigns,
                'campaigns_sent': total_campaigns,
                'campaigns_found': len(fetched_ids),
                'known_campaigns': len(known_ids),
                'period_begin': begin,
                'period_end': end,
                'days_received': 0,
                'spend_loaded': 0.0,
                'api_cooldown_status': api_cooldown_status,
                'next_safe_seconds': int(str(api_cooldown_status).split(':', 1)[1]) if api_cooldown_status and ':' in str(api_cooldown_status) else None,
            })
            print(f'ADS RESULT status={batch_status} loaded=0')
            return 0, batch_status

        prepared = _prepare_advertising_rows(cur, telegram_id, payload)
        parsed_rows = prepared['parsed_rows']
        spend_loaded = prepared['spend_loaded']
        response_days_count = prepared['response_days_count']
        response_advert_ids = set(prepared['response_advert_ids'])
        saved, replaced_scopes = _upsert_advertising_rows(cur, parsed_rows) if parsed_rows else (0, {})

        missing_ids = [advert_id for advert_id in batch_ids if int(advert_id) not in response_advert_ids]
        effective_status = 'SUCCESS' if not missing_ids else 'ADS_PARTIAL_MISSING_IDS'
        known_after = _merge_advert_id_sources(batch_ids, response_advert_ids)
        _remember_known_advert_ids(telegram_id, known_after)

        conn.commit()
        conn.close()
        conn = None
        details = {
            'status': effective_status,
            'total_campaigns': total_campaigns,
            'campaigns_sent': total_campaigns,
            'campaigns_found': len(fetched_ids),
            'known_campaigns': len(known_ids),
            'period_begin': begin,
            'period_end': end,
            'days_received': response_days_count,
            'advert_ids_received': len(response_advert_ids),
            'advert_ids_sent': total_campaigns,
            'advert_ids_missing': len(missing_ids),
            'missing_advert_ids': missing_ids[:200],
            'replaced_campaign_dates': sum(len(v) for v in replaced_scopes.values()),
            'spend_loaded': round(spend_loaded, 2),
            'loaded': saved,
            'api_cooldown_status': f'ADS_STEP_COOLDOWN:{ADS_SAFE_MIN_COOLDOWN_SECONDS}',
            'next_safe_seconds': ADS_SAFE_MIN_COOLDOWN_SECONDS,
        }
        _set_last_ads_run_details(telegram_id, details)
        print(f'ADS RESULT status={effective_status} loaded={saved}')
        return saved, effective_status
    except Exception as exc:
        _log_ads_exception(exc)
        if conn is not None:
            conn.close()
        raise


def load_advertising(telegram_id, token, days=30, token_source='unknown'):
    return _load_advertising_range(telegram_id, token, days, token_source=token_source, allow_cooldown=True)


def backfill_advertising_period(telegram_id, token, begin, end, token_source='unknown'):
    return _load_advertising_range(telegram_id, token, (str(begin), str(end)), token_source=token_source, allow_cooldown=True)


def load_ads_for_user(telegram_id=None, wb_token=None, days=30):
    init_db()
    token = wb_token or WB_TOKEN
    token_source = 'function_arg.wb_token' if wb_token else 'config.WB_TOKEN'
    if not token:
        update_sync_status(telegram_id or 0, 'advertising', 'NO_WB_TOKEN')
        return 0, {'overall': 'ERROR', 'blocks': {'advertising': {'status': 'NO_WB_TOKEN', 'loaded': 0}}}
    telegram_id = telegram_id or 0
    lock_acquired = _acquire_local_sync_lock(telegram_id, 'advertising', max_age_minutes=30)
    if not lock_acquired:
        ads_n, ads_status = 0, 'ADS_COOLDOWN:0'
    else:
        try:
            ads_n, ads_status = _run_block(telegram_id, 'advertising', load_advertising, telegram_id, token, days, token_source=token_source, cooldown_caller='load_ads_for_user->load_advertising')
        finally:
            _release_local_sync_lock(telegram_id, 'advertising')
    update_sync_status(telegram_id, 'advertising', ads_status)
    status = _build_update_status({'advertising': {'status': ads_status, 'loaded': ads_n}})
    details = _get_last_ads_run_details(telegram_id)
    if details:
        status['blocks']['advertising']['details'] = details
    save_update(format_update_status(status), 0, telegram_id, 0, 0, ads_n, 0)
    return ads_n, status


def load_sales_for_user(telegram_id=None, wb_token=None, days=30, verbose=True, load_expenses=True):
    init_db()
    token = wb_token or WB_TOKEN
    token_source = 'function_arg.wb_token' if wb_token else 'config.WB_TOKEN'
    if not token:
        save_update('NO_WB_TOKEN', 0, telegram_id)
        return 0, 'NO_WB_TOKEN'

    telegram_id = telegram_id or 0
    sales_n, sales_status = _run_block(telegram_id, 'sales', load_sales, telegram_id, token, days)
    orders_n, orders_status = _run_block(telegram_id, 'orders', load_orders, telegram_id, token, days)
    stocks_n, stocks_status = _run_block(telegram_id, 'stocks', load_stocks, telegram_id, token)
    update_sync_status(telegram_id, 'sales', sales_status)
    update_sync_status(telegram_id, 'orders', orders_status)
    update_sync_status(telegram_id, 'stocks', stocks_status)

    expenses_n = 0
    ads_n = 0
    finance_status = 'SKIPPED'
    ads_status = 'SKIPPED'
    if load_expenses:
        expenses_n, finance_status = _run_block(telegram_id, 'finance', load_finance_expenses, telegram_id, token, days)
        ads_n, ads_status = _run_block(telegram_id, 'advertising', load_advertising, telegram_id, token, days, token_source=token_source, cooldown_caller='load_sales_for_user->load_advertising')
        update_sync_status(telegram_id, 'finance', finance_status)
        update_sync_status(telegram_id, 'advertising', ads_status)

    status = _build_update_status({
        'sales': {'status': sales_status, 'loaded': sales_n},
        'orders': {'status': orders_status, 'loaded': orders_n},
        'stocks': {'status': stocks_status, 'loaded': stocks_n},
        'finance': {'status': finance_status, 'loaded': expenses_n},
        'advertising': {'status': ads_status, 'loaded': ads_n},
    })
    details = _get_last_ads_run_details(telegram_id)
    if details:
        status['blocks']['advertising']['details'] = details
    save_update(format_update_status(status), sales_n, telegram_id, orders_n, expenses_n, ads_n, stocks_n)
    return sales_n, status


if __name__ == '__main__':
    print(load_sales_for_user(verbose=True, load_expenses=True))
