from .design import PRODUCT_NAME, title


def connect_intro_text() -> str:
    return (
        f"{title('🔐', 'Подключение кабинета WB')}\n\n"
        f"Чтобы {PRODUCT_NAME} начал анализировать ваш бизнес, подключите API-ключ Wildberries.\n\n"
        "Как подключить:\n"
        "1. Откройте кабинет продавца Wildberries.\n"
        "2. Создайте API-ключ с правами на чтение.\n"
        "3. Отправьте его командой:\n\n"
        "/connect ВАШ_API_КЛЮЧ\n\n"
        "Безопасность:\n"
        "Ключ хранится в зашифрованном виде."
    )


def update_no_cabinet_text() -> str:
    return (
        "⚠ Кабинет WB не подключён.\n\n"
        "Чтобы обновить данные, сначала подключите API-ключ:\n"
        "/connect"
    )


def update_started_text() -> str:
    return (
        "🔄 Обновляю данные WB.\n\n"
        "Это может занять несколько минут.\n"
        "После обновления откройте /home."
    )


def stocks_empty_text() -> str:
    return (
        "📦 Остатки\n\n"
        "Данные по остаткам пока не загружены.\n\n"
        "Что сделать:\n"
        "1. Запустить обновление: /update\n"
        "2. Проверить подключение WB: /profile"
    )
