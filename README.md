# VOOGLII / WildberriesAgent

## Запуск
```powershell
py -m pip install -r requirements.txt
python create_products_table.py
$env:BOT_TOKEN="your_telegram_bot_token"
$env:BOT_USERNAME="vooglii_bot"
python telegram_bot.py
```

## Переменные окружения
- BOT_TOKEN — токен Telegram-бота VOOGLII
- BOT_USERNAME — username Telegram-бота VOOGLII
- WB_TOKEN — резервный WB API токен
- ADMIN_IDS — Telegram ID админов через запятую
- PAYMENT_PROVIDER_TOKEN — токен платежного провайдера Telegram
- PRO_PRICE_RUB=690

## Telegram configuration
Пример:

```text
BOT_TOKEN=your_telegram_bot_token
BOT_USERNAME=vooglii_bot
```

Токен Telegram-бота не должен храниться в исходном коде. Перед запуском задайте `BOT_TOKEN` и при необходимости `BOT_USERNAME` через environment variables.

## RBAC
- Роли платформы: `owner`, `admin`, `manager`, `analyst`, `viewer`
- Backend RBAC map и audit hooks: `analytics/rbac.py`
- Временная интеграционная точка для actor resolution: заголовок `X-VOOGLII-Actor-Id`
- Детали реализации и текущие ограничения: `RBAC_ARCHITECTURE.md`

## Тарифы
FREE: базовые отчёты, история 7 дней.  
PRO: все команды, реклама, P&L, экспорт, AI, уведомления, конкуренты-заготовки.

## Команды
/start /menu /connect /update /ceo /morning /report /orders /funnel /advert /product /stocks /stock /analytics /pnl /problems /advice /plan /compare /cashflow /prices /export /notify /profile /tariff /buy /ref /admin
