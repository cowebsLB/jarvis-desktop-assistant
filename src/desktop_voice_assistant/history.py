from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .config import APP_DIR


HISTORY_PATH = APP_DIR / "history.jsonl"


@dataclass
class HistoryEvent:
    kind: str
    data: dict[str, Any]
    pinned: bool = False
    summary: str | None = None
    correlation_id: str | None = None
    conversation_id: str | None = None
    state_from: str | None = None
    state_to: str | None = None

    def to_record(self) -> dict[str, Any]:
        return {
            "id": str(uuid4()),
            "timestamp": datetime.now(UTC).isoformat(),
            "kind": self.kind,
            "pinned": self.pinned,
            "summary": self.summary,
            "correlation_id": self.correlation_id,
            "conversation_id": self.conversation_id,
            "state_from": self.state_from,
            "state_to": self.state_to,
            "data": self.data,
        }


class HistoryRecorder:
    def __init__(self, path: Path = HISTORY_PATH) -> None:
        self.path = path
        APP_DIR.mkdir(parents=True, exist_ok=True)
        self._subscribers: list = []

    def append(self, event: HistoryEvent) -> None:
        record = event.to_record()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")
        for subscriber in list(self._subscribers):
            subscriber(record)

    def subscribe(self, callback) -> None:
        self._subscribers.append(callback)
