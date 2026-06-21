from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import APP_DIR

LOGGER = logging.getLogger(__name__)
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
        self._preferences: dict[str, Any] = {
            "favorite_sites": {},
            "preferred_location": "",
            "preferred_apps": {}
        }
        self._turns: list[dict[str, str]] = []
        self._history_summary: str = ""
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

    # --- Preferences API ---

    def get_preference(self, key: str, default: Any = None) -> Any:
        return self._preferences.get(key, default)

    def set_preference(self, key: str, value: Any) -> None:
        self._preferences[key] = value
        self._save()

    def get_favorite_site(self, name: str) -> str | None:
        return self._preferences.get("favorite_sites", {}).get(name)

    def set_favorite_site(self, name: str, url: str) -> None:
        if "favorite_sites" not in self._preferences:
            self._preferences["favorite_sites"] = {}
        self._preferences["favorite_sites"][name] = url
        self._save()

    def get_preferred_app(self, name: str) -> str | None:
        return self._preferences.get("preferred_apps", {}).get(name)

    def set_preferred_app(self, name: str, path: str) -> None:
        if "preferred_apps" not in self._preferences:
            self._preferences["preferred_apps"] = {}
        self._preferences["preferred_apps"][name] = path
        self._save()

    # --- Conversational Turn Memory API ---

    def add_turn(self, user_query: str, assistant_reply: str, llm_assistant=None) -> None:
        if not user_query or not assistant_reply:
            return
        self._turns.append({"user": user_query, "assistant": assistant_reply})
        
        # Summarize when turns exceed limit to keep context compact
        if len(self._turns) >= 5 and llm_assistant is not None:
            self._history_summary = self._summarize_turns(llm_assistant)
            self._turns.clear()
            
        self._save()

    def get_turns_context(self) -> str:
        context = ""
        if self._history_summary:
            context += f"Background of previous turns: {self._history_summary}\n"
        if self._turns:
            context += "Recent turns in this session:\n"
            for turn in self._turns:
                context += f"User: {turn['user']}\nJarvis: {turn['assistant']}\n"
        return context

    def _summarize_turns(self, llm_assistant) -> str:
        prompt = (
            "Summarize the following part of the conversation compactly in a few sentences, "
            "focusing on user preferences, topics discussed, or actions taken:\n"
        )
        for turn in self._turns:
            prompt += f"User: {turn['user']}\nJarvis: {turn['assistant']}\n"
            
        if self._history_summary:
            prompt = f"Existing background context: {self._history_summary}\n\n" + prompt
            
        try:
            summary = llm_assistant.answer(prompt)
            LOGGER.info("Conversation history summarized successfully.")
            return summary
        except Exception as exc:
            LOGGER.error("Failed to summarize conversation turns: %s", exc)
            return self._history_summary

    def snapshot(self) -> dict[str, dict[str, int | str]]:
        return {
            key: {"canonical": value.canonical, "uses": value.uses}
            for key, value in sorted(self._aliases.items())
        }

    def _load(self) -> None:
        if not self.path.exists():
            self._save()
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            self._aliases = {
                key: LearnedAlias(
                    canonical=value["canonical"],
                    uses=int(value.get("uses", 0)),
                )
                for key, value in payload.get("aliases", {}).items()
            }
            self._preferences = payload.get("preferences", {
                "favorite_sites": {},
                "preferred_location": "",
                "preferred_apps": {}
            })
            self._turns = payload.get("turns", [])
            self._history_summary = payload.get("history_summary", "")
        except Exception as exc:
            LOGGER.exception("Failed to load app memory file: %s", exc)

    def _save(self) -> None:
        payload = {
            "aliases": self.snapshot(),
            "preferences": self._preferences,
            "turns": self._turns,
            "history_summary": self._history_summary,
        }
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
