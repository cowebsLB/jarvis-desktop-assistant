from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class RuntimeState(str, Enum):
    BOOTING = "booting"
    IDLE = "idle"
    WAKE_LISTENING = "wake_listening"
    CAPTURING_COMMAND = "capturing_command"
    TRANSCRIBING = "transcribing"
    UNDERSTANDING = "understanding"
    CLARIFYING = "clarifying"
    PLANNING = "planning"
    RESEARCHING = "researching"
    FETCHING_SOURCES = "fetching_sources"
    RANKING_SOURCES = "ranking_sources"
    SUMMARIZING_SOURCES = "summarizing_sources"
    ARCHIVING_SOURCES = "archiving_sources"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    EXECUTING = "executing"
    SPEAKING = "speaking"
    AWAITING_FOLLOWUP = "awaiting_followup"
    PROACTIVE_PENDING = "proactive_pending"
    SUSPENDED = "suspended"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"


@dataclass
class AssistantRequest:
    transcript: str
    timestamp: datetime
    source: str = "microphone"
    audio_seconds: float | None = None


@dataclass
class IntentResult:
    intent: str
    confidence: float
    slots: dict[str, str] = field(default_factory=dict)


@dataclass
class ActionResult:
    success: bool
    message: str
    spoken_reply: str | None = None
    sources: list["ResearchSource"] = field(default_factory=list)
    opened_target: str | None = None


@dataclass
class OpenTargetPreview:
    requested_target: str
    resolved_target: str
    exact_match: bool = False
    fuzzy_match: str | None = None
    launchable: bool = False


@dataclass
class ResearchSource:
    title: str
    url: str
    snippet: str


@dataclass
class ResearchResult:
    query: str
    answer: str
    spoken: str
    sources: list[ResearchSource] = field(default_factory=list)
    from_archive: bool = False


@dataclass
class TranscriptResult:
    text: str
    audio_seconds: float | None = None
    ended_early: bool = False
    confidence: float = 1.0
