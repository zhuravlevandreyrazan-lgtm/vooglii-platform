from __future__ import annotations

import importlib
import sys
from pathlib import Path


def get_bot():
    main_module = sys.modules.get("__main__")
    main_file = getattr(main_module, "__file__", None)
    if main_file and Path(main_file).name == "telegram_bot.py":
        return main_module
    return importlib.import_module("telegram_bot")
