# SECURITY MODEL

## Token Storage

- WB-токены больше не сохраняются в SQLite в открытом виде.
- Для хранения используется `security/token_crypto.py`.
- Формат хранения: `enc:v1:...`
- Ключ берется из `VOOGLII_TOKEN_ENCRYPTION_KEY`.
- В production запуск без ключа шифрования запрещен.

## Access Control

- Центральная permission-модель находится в `security/permissions.py`.
- Поддерживаемые роли:
  - `owner`
  - `admin`
  - `manager`
  - `viewer`
  - `support`
  - `developer`
- `ADMIN_IDS` сохранен как bootstrap fallback.

## Logging Policy

- Маскирование чувствительных данных выполняется через `security/logging.py`.
- В логах запрещено хранить:
  - WB tokens
  - Telegram bot token
  - Authorization headers
  - Bearer tokens
  - cookies
  - API keys

## Audit Trail

- Privileged actions пишутся через `security/audit_log.py`.
- Логируются:
  - команда
  - actor user_id
  - роль
  - действие
  - результат

## Runtime Safety

- Healthcheck проверяет:
  - `BOT_TOKEN`
  - доступность SQLite
  - `SELECT 1`
  - heartbeat бота в production
- SQLite переведен на:
  - `journal_mode = WAL`
  - `busy_timeout = 5000`
  - `synchronous = NORMAL`

