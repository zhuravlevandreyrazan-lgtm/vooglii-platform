from __future__ import annotations

from typing import Protocol


class StorageProvider(Protocol):
    def store_artifact(self, name: str, path: str) -> str: ...
