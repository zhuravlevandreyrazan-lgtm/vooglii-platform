from __future__ import annotations

from typing import Protocol


class BackupProvider(Protocol):
    def create_backup(self, target: str) -> str: ...
