from __future__ import annotations

from typing import Protocol


class RestoreProvider(Protocol):
    def restore_backup(self, source: str) -> str: ...
