import sqlite3, secrets, string
from datetime import datetime, timedelta
from config import DB_NAME, DEFAULT_TARIFF
from db_manager import get_conn, init_db, _is_readonly_db_error
from security.permissions import normalize_role
from security.token_crypto import decrypt_token, encrypt_token, is_encrypted_token, validate_wb_token

ROLES = {'owner','admin','manager','viewer','support','developer','accountant'}
PRO_FEATURES = {'advert','pnl','export','advice','problems','plan','compare','cashflow','prices','admin_roles','competitors','notifications'}
FREE_FEATURES = {'start','help','menu','connect','disconnect','update','report','today','week','month','product','products','stocks','orders','funnel','status','profile','tariff','buy','pro','ref','dashboard','home','business','finance','analytics','system','advisor','forecast'}


def _conn(): init_db(); return get_conn()
def _now(): return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
def _code(): return ''.join(secrets.choice(string.ascii_uppercase+string.digits) for _ in range(8))


def _default_user_row(telegram_id, username='unknown'):
    return (telegram_id, username, None, 'FREE', 1, None, None, 'owner', None, None, None)


def _fetch_user_row(telegram_id):
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        '''SELECT telegram_id,username,wb_token,tariff,is_active,created_at,updated_at,role,subscription_until,referral_code,referred_by FROM users WHERE telegram_id=?''',
        (telegram_id,),
    )
    row = cur.fetchone()
    conn.close()
    return row


def _safe_optional_write(write_fn):
    try:
        return write_fn()
    except sqlite3.OperationalError as exc:
        if _is_readonly_db_error(exc):
            return False
        raise

def ensure_user(telegram_id, username='unknown', ref_code=None):
    def _write():
        conn=_conn(); cur=conn.cursor(); cur.execute('SELECT telegram_id FROM users WHERE telegram_id=?',(telegram_id,)); exists=cur.fetchone()
        if not exists:
            referrer=None
            if ref_code:
                cur.execute('SELECT telegram_id FROM users WHERE referral_code=?',(ref_code.upper(),)); row=cur.fetchone(); referrer=row[0] if row else None
            code=_code()
            cur.execute('''INSERT INTO users(telegram_id,username,tariff,is_active,role,referral_code,referred_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)''',(telegram_id,username,DEFAULT_TARIFF,1,'owner',code,referrer,_now(),_now()))
            if referrer:
                cur.execute('INSERT OR IGNORE INTO referrals(referrer_id,invited_id,bonus_days,created_at) VALUES(?,?,30,?)',(referrer,telegram_id,_now()))
        else:
            cur.execute('UPDATE users SET username=COALESCE(?,username), updated_at=? WHERE telegram_id=?',(username,_now(),telegram_id))
        conn.commit(); conn.close()
        return True
    return _safe_optional_write(_write)

def save_user(telegram_id, username, wb_token):
    token = encrypt_token(validate_wb_token(wb_token))
    ensure_user(telegram_id, username); conn=_conn(); cur=conn.cursor(); cur.execute('UPDATE users SET username=?, wb_token=?, updated_at=? WHERE telegram_id=?',(username,token,_now(),telegram_id)); conn.commit(); conn.close()

def get_user(telegram_id):
    row = _fetch_user_row(telegram_id)
    if row:
        return row
    ensure_user(telegram_id)
    row = _fetch_user_row(telegram_id)
    return row or _default_user_row(telegram_id)

def get_user_token(telegram_id):
    u=get_user(telegram_id)
    token = u[2] if u else None
    if not token:
        return None
    if is_encrypted_token(token):
        return decrypt_token(token)
    plain_token = validate_wb_token(token)
    try:
        save_user(telegram_id, (u[1] if u else 'unknown') or 'unknown', plain_token)
    except Exception:
        pass
    return plain_token

def _expired(u):
    if not u or (u[3] or 'FREE').upper()!='PRO' or not u[8]: return False
    try: return datetime.strptime(u[8], '%Y-%m-%d') < datetime.now()
    except Exception: return False

def downgrade_if_expired(telegram_id):
    u=get_user(telegram_id)
    if _expired(u):
        _safe_optional_write(lambda: set_user_access(telegram_id,'FREE',1,None))

def user_has_access(telegram_id, feature=None):
    u=get_user(telegram_id)
    if not u or int(u[4] or 0)!=1: return False
    tariff='FREE' if _expired(u) else (u[3] or 'FREE').upper()
    if not feature: return True
    return tariff=='PRO' or feature in FREE_FEATURES

def is_pro(telegram_id):
    u=get_user(telegram_id); return bool(u and not _expired(u) and (u[3] or '').upper()=='PRO' and int(u[4] or 0)==1)

def set_user_access(telegram_id, tariff='PRO', is_active=1, subscription_until=None):
    ensure_user(telegram_id); tariff='PRO' if str(tariff).upper()=='PRO' else 'FREE'
    conn=_conn(); cur=conn.cursor(); cur.execute('UPDATE users SET tariff=?, is_active=?, subscription_until=?, updated_at=? WHERE telegram_id=?',(tariff,int(is_active),subscription_until,_now(),telegram_id)); conn.commit(); conn.close()

def extend_pro(telegram_id, days=30):
    u=get_user(telegram_id); base=datetime.now()
    if u and u[8]:
        try:
            old=datetime.strptime(u[8], '%Y-%m-%d')
            if old>base: base=old
        except Exception: pass
    until=(base+timedelta(days=days)).strftime('%Y-%m-%d')
    set_user_access(telegram_id,'PRO',1,until); return until

def set_role(telegram_id, role):
    role = normalize_role(role)
    conn=_conn(); cur=conn.cursor(); cur.execute('UPDATE users SET role=?, updated_at=? WHERE telegram_id=?',(role,_now(),telegram_id)); conn.commit(); conn.close()

def get_all_users():
    conn=_conn(); cur=conn.cursor(); cur.execute('SELECT telegram_id,username,tariff,is_active,created_at,subscription_until,role FROM users ORDER BY created_at DESC'); rows=cur.fetchall(); conn.close(); return rows

def get_ref_stats(telegram_id):
    u=get_user(telegram_id); conn=_conn(); cur=conn.cursor(); cur.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id=?',(telegram_id,)); cnt=cur.fetchone()[0]; conn.close(); return (u[9] if u else '-', cnt)


def clear_user_token(telegram_id):
    conn = _conn()
    cur = conn.cursor()
    cur.execute('UPDATE users SET wb_token=NULL, updated_at=? WHERE telegram_id=?', (_now(), telegram_id))
    conn.commit()
    conn.close()


def get_active_user_tokens(telegram_id=None):
    conn = _conn()
    cur = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    query = '''
        SELECT telegram_id, username, wb_token
        FROM users
        WHERE is_active=1
          AND wb_token IS NOT NULL
          AND TRIM(wb_token)!=''
          AND (
              UPPER(COALESCE(tariff,'FREE'))!='PRO'
              OR subscription_until IS NULL
              OR subscription_until=''
              OR subscription_until>=?
          )
    '''
    params = [today]
    if telegram_id is not None:
        query += ' AND telegram_id=?'
        params.append(telegram_id)
    query += ' ORDER BY telegram_id'
    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    conn.close()
    result = []
    for user_id, _username, token in rows:
        try:
            result.append((int(user_id), decrypt_token(token) if is_encrypted_token(token) else validate_wb_token(token)))
        except Exception:
            continue
    return result
