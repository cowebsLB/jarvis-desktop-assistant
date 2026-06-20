from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from .models import IntentResult, ResearchSource


@dataclass
class PendingConfirmation:
    intent: IntentResult
    prompt: str


@dataclass
class PendingClarification:
    intent_name: str
    slot_name: str
    prompt: str


@dataclass
class SessionSnapshot:
    conversation_id: str
    followup_until: datetime | None = None
    last_intent: str | None = None
    last_query: str | None = None
    last_open_target: str | None = None
    last_sources: list[ResearchSource] = field(default_factory=list)
    pending_confirmation: PendingConfirmation | None = None
    pending_clarification: PendingClarification | None = None

    def is_followup_active(self, now: datetime | None = None) -> bool:
        if self.followup_until is None:
            return False
        compare_time = now or datetime.now(UTC)
        return compare_time <= self.followup_until


class SessionManager:
    def __init__(self, followup_seconds: int = 45) -> None:
        self.followup_seconds = followup_seconds
        self.snapshot = SessionSnapshot(conversation_id=str(uuid4()))

    def conversation_id_for_turn(self) -> str:
        if self.snapshot.is_followup_active():
            return self.snapshot.conversation_id
        self.snapshot = SessionSnapshot(conversation_id=str(uuid4()))
        return self.snapshot.conversation_id

    def mark_result(
        self,
        *,
        intent: str,
        query: str | None = None,
        open_target: str | None = None,
        sources: list[ResearchSource] | None = None,
    ) -> None:
        self.snapshot.last_intent = intent
        self.snapshot.last_query = query
        self.snapshot.last_open_target = open_target
        self.snapshot.last_sources = list(sources or [])
        self.snapshot.followup_until = datetime.now(UTC) + timedelta(seconds=self.followup_seconds)

    def clear_followup(self) -> None:
        self.snapshot.followup_until = None

    def resolve_followup(self, normalized_text: str) -> tuple[str, dict[str, str]] | None:
        if not self.snapshot.is_followup_active():
            return None

        if normalized_text in {"open it", "open that", "open the source", "open the first source"}:
            if self.snapshot.last_sources:
                source = self.snapshot.last_sources[0]
                return "open_source", {"url": source.url, "title": source.title}
            if self.snapshot.last_open_target:
                return "open_target", {"target": self.snapshot.last_open_target}

        if normalized_text in {"summarize that", "summarize it", "what do you know about that"}:
            if self.snapshot.last_query:
                return "recall_memory", {"query": self.snapshot.last_query}

        if normalized_text in {"search again", "search that again"}:
            if self.snapshot.last_query:
                return "web_search", {"query": self.snapshot.last_query}

        if normalized_text in {"search again but for today", "search that again but for today"}:
            if self.snapshot.last_query:
                return "web_search", {"query": f"{self.snapshot.last_query} today"}

        return None

    def set_confirmation(self, intent: IntentResult, prompt: str) -> None:
        self.snapshot.pending_confirmation = PendingConfirmation(intent=intent, prompt=prompt)
        self.snapshot.followup_until = datetime.now(UTC) + timedelta(seconds=self.followup_seconds)

    def consume_confirmation(self, normalized_text: str) -> tuple[str, IntentResult | None] | None:
        pending = self.snapshot.pending_confirmation
        if pending is None:
            return None

        if normalized_text in {"yes", "yeah", "yep", "confirm", "do it", "go ahead"}:
            self.snapshot.pending_confirmation = None
            return (
                "confirmed",
                IntentResult(
                    pending.intent.intent,
                    pending.intent.confidence,
                    {**pending.intent.slots, "_confirmed": "true"},
                ),
            )

        if normalized_text in {"no", "nope", "cancel", "stop", "nevermind", "never mind"}:
            self.snapshot.pending_confirmation = None
            return ("cancelled", None)

        return None

    def set_clarification(self, intent_name: str, slot_name: str, prompt: str) -> None:
        self.snapshot.pending_clarification = PendingClarification(
            intent_name=intent_name,
            slot_name=slot_name,
            prompt=prompt,
        )
        self.snapshot.followup_until = datetime.now(UTC) + timedelta(seconds=self.followup_seconds)

    def consume_clarification(self, transcript: str) -> IntentResult | None:
        pending = self.snapshot.pending_clarification
        if pending is None:
            return None
        self.snapshot.pending_clarification = None
        return IntentResult(pending.intent_name, 0.95, {pending.slot_name: transcript.strip()})
