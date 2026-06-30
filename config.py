import os

DB_NAME = os.getenv('DB_NAME', 'wildberries.db')
BOT_TOKEN = os.getenv('BOT_TOKEN', '').strip()
BOT_USERNAME = os.getenv('BOT_USERNAME', 'unknown').strip() or 'unknown'
WB_TOKEN = os.getenv('WB_TOKEN', '').strip()
PAYMENT_PROVIDER_TOKEN = os.getenv('PAYMENT_PROVIDER_TOKEN', '')
ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '658486226').replace(' ', '').split(',') if x]
PRO_PRICE_RUB = int(os.getenv('PRO_PRICE_RUB', '690'))
DEFAULT_TARIFF = 'FREE'
FREE_HISTORY_DAYS = 7
