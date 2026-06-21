from __future__ import annotations

import json
from pathlib import Path

from .config import APP_DIR


SECRETS_PATH = APP_DIR / "secrets.json"


class SecretStore:
    def __init__(self, path: Path = SECRETS_PATH) -> None:
        self.path = path

    def load(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def get(self, key: str) -> str | None:
        value = self.load().get(key)
        return value.strip() if isinstance(value, str) and value.strip() else None

    def set(self, key: str, value: str) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        data = self.load()
        data[key] = value.strip()
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")
