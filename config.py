import os
from pathlib import Path


def _resolve_db_name() -> str:
    raw_db_dir = str(os.getenv('DB_DIR', '') or '').strip()
    if raw_db_dir:
        storage_dir = Path(raw_db_dir).expanduser()
        if not storage_dir.is_absolute():
            storage_dir = Path(__file__).resolve().parent / storage_dir
    else:
        storage_dir = Path(__file__).resolve().parent / 'storage'
    storage_dir.mkdir(parents=True, exist_ok=True)

    raw_db_name = str(os.getenv('DB_NAME', '') or '').strip()
    if raw_db_name:
        db_path = Path(raw_db_name)
        if not db_path.is_absolute():
            # Treat a bare filename as a persistent DB file inside storage/.
            if db_path.parent == Path('.'):
                db_path = storage_dir / db_path.name
            else:
                db_path = Path(__file__).resolve().parent / db_path
    else:
        db_path = storage_dir / 'wildberries.db'

    db_path.parent.mkdir(parents=True, exist_ok=True)
    return str(db_path)


DB_NAME = _resolve_db_name()
BOT_TOKEN = os.getenv('BOT_TOKEN', '').strip()
BOT_USERNAME = os.getenv('BOT_USERNAME', 'unknown').strip() or 'unknown'
WB_TOKEN = os.getenv('WB_TOKEN', '').strip()
PAYMENT_PROVIDER_TOKEN = os.getenv('PAYMENT_PROVIDER_TOKEN', '')
ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '658486226').replace(' ', '').split(',') if x]
PRO_PRICE_RUB = int(os.getenv('PRO_PRICE_RUB', '690'))
DEFAULT_TARIFF = 'FREE'
FREE_HISTORY_DAYS = 7
