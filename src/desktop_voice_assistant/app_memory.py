from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .config import APP_DIR


APP_MEMORY_PATH = APP_DIR / "app_memory.json"


@dataclass
class LearnedAlias:
    canonical: str
    uses: int = 0


class AppMemoryStore:
    def __init__(self, path: Path = APP_MEMORY_PATH) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._aliases: dict[str, LearnedAlias] = {}
        self._load()

    def resolve(self, spoken_name: str) -> str | None:
        alias = self._aliases.get(spoken_name)
        if not alias:
            return None
        return alias.canonical

    def remember(self, spoken_name: str, canonical_name: str) -> None:
        if not spoken_name or not canonical_name or spoken_name == canonical_name:
            return
        entry = self._aliases.get(spoken_name)
        if entry:
            entry.canonical = canonical_name
            entry.uses += 1
        else:
            self._aliases[spoken_name] = LearnedAlias(canonical=canonical_name, uses=1)
        self._save()

    def snapshot(self) -> dict[str, dict[str, int | str]]:
        return {
            key: {"canonical": value.canonical, "uses": value.uses}
            for key, value in sorted(self._aliases.items())
        }

    def _load(self) -> None:
        if not self.path.exists():
            self._save()
            return
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        self._aliases = {
            key: LearnedAlias(
                canonical=value["canonical"],
                uses=int(value.get("uses", 0)),
            )
            for key, value in payload.get("aliases", {}).items()
        }

    def _save(self) -> None:
        payload = {"aliases": self.snapshot()}
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
