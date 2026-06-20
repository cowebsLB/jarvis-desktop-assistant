from __future__ import annotations

import re

from .models import IntentResult


class IntentRouter:
    def route(self, transcript: str) -> IntentResult:
        text = transcript.strip()
        normalized = self._normalize_text(text)

        if match := re.match(r"^(type|dictate)\s+(.+)$", normalized, re.IGNORECASE):
            dictated_text = self._extract_after_command(text, match.group(1))
            return IntentResult("dictate", 0.99, {"text": dictated_text})

        if expression := self._extract_calculation_expression(normalized):
            return IntentResult("calculate", 0.96, {"expression": expression})

        if folder_target := self._extract_folder_target(normalized):
            return IntentResult("open_folder", 0.95, {"target": folder_target})

        if file_target := self._extract_file_target(normalized):
            return IntentResult("open_file", 0.92, {"target": file_target})

        if target := self._extract_open_target(normalized):
            return IntentResult("open_target", 0.95, {"target": target})

        if match := re.search(r"\b(search (the )?(web|internet) for|google)\s+(.+)$", normalized):
            return IntentResult("web_search", 0.95, {"query": match.group(4).strip()})

        if match := re.search(r"\b(summarize|what do you know about|what have you found about)\s+(.+)$", normalized):
            return IntentResult("recall_memory", 0.9, {"query": match.group(2).strip()})

        if self._is_weather_request(normalized):
            return IntentResult("weather", 0.95, {"location": self._extract_location(text)})

        if self._is_time_sensitive_search(normalized):
            return IntentResult("web_search", 0.9, {"query": text})

        if any(normalized.startswith(prefix) for prefix in ("what", "who", "when", "where", "why", "how")):
            return IntentResult("qa", 0.8, {"query": text})

        if any(
            normalized.startswith(prefix)
            for prefix in ("tell me", "can you tell me", "check", "look up", "find out")
        ):
            return IntentResult("qa", 0.7, {"query": text})

        if normalized.endswith("?"):
            return IntentResult("qa", 0.75, {"query": text})

        return IntentResult("unsupported", 0.2, {"query": text})

    def normalize_for_followup(self, transcript: str) -> str:
        return self._normalize_text(transcript.strip())

    @staticmethod
    def _normalize_text(text: str) -> str:
        normalized = text.lower().strip()
        normalized = re.sub(r"[,\.!]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        normalized = re.sub(r"^(hey|okay|ok)\s+jarvis\b", "", normalized).strip()
        normalized = re.sub(
            r"^(can you|could you|would you|will you|please|hey|ok|okay|jarvis)\b",
            "",
            normalized,
        ).strip()
        normalized = re.sub(r"\b(please|for me|right now)\b", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    @staticmethod
    def _extract_after_command(original_text: str, command: str) -> str:
        match = re.search(rf"\b{re.escape(command)}\b(.+)$", original_text, re.IGNORECASE)
        if not match:
            return original_text.strip()
        extracted = match.group(1).strip(" ,.!")
        extracted = re.sub(r"\b(please|for me|right now)\b", "", extracted, flags=re.IGNORECASE)
        return re.sub(r"\s+", " ", extracted).strip(" ,.!")

    @staticmethod
    def _is_time_sensitive_search(text: str) -> bool:
        time_sensitive_terms = (
            "weather",
            "forecast",
            "temperature",
            "rain",
            "news",
            "latest",
            "today",
            "today's",
            "tomorrow",
            "current",
        )
        searchish_prefixes = ("check", "look up", "find", "tell me", "what's", "whats")
        return any(term in text for term in time_sensitive_terms) and (
            any(text.startswith(prefix) for prefix in searchish_prefixes) or " in " in text
        )

    @staticmethod
    def _is_weather_request(text: str) -> bool:
        return any(term in text for term in ("weather", "forecast", "temperature", "rain")) and not text.startswith(
            "search "
        )

    @staticmethod
    def _extract_location(text: str) -> str:
        normalized = text.strip()
        lowered = normalized.lower()
        for marker in (" in ", " for ", " at "):
            if marker in lowered:
                location = normalized[lowered.rfind(marker) + len(marker) :].strip(" ?.!,")
                location = re.sub(r"\b(please|for me|right now)\b", "", location, flags=re.IGNORECASE)
                location = re.sub(r"\s+", " ", location).strip(" ,.!")
                return location

        for alias, canonical in {
            "lebanon": "Lebanon",
            "leb": "Lebanon",
            "beirut": "Beirut, Lebanon",
        }.items():
            if re.search(rf"\b{re.escape(alias)}\b", lowered):
                return canonical
        return ""

    @staticmethod
    def _extract_open_target(text: str) -> str | None:
        patterns = (
            r"\b(?:open|launch|start)\s+(.+)$",
            r"\b(?:go to|visit)\s+(.+)$",
        )
        for pattern in patterns:
            if match := re.search(pattern, text):
                return match.group(1).strip()
        return None

    @staticmethod
    def _extract_folder_target(text: str) -> str | None:
        patterns = (
            r"\b(?:open|show)\s+(.+?)\s+folder$",
            r"\bopen\s+(desktop|documents|document|downloads|download|music|pictures|photos|videos|home)$",
        )
        for pattern in patterns:
            if match := re.search(pattern, text):
                return match.group(1).strip()
        return None

    @staticmethod
    def _extract_file_target(text: str) -> str | None:
        patterns = (
            r"\b(?:open|find)\s+(?:the\s+)?file\s+(.+)$",
            r"\bopen\s+document\s+(.+)$",
        )
        for pattern in patterns:
            if match := re.search(pattern, text):
                return match.group(1).strip()
        return None

    @staticmethod
    def _extract_calculation_expression(text: str) -> str | None:
        patterns = (
            r"^(?:calculate|compute|evaluate)\s+(.+)$",
            r"^(?:what is|whats)\s+(-?[\d\w\s\.\+\-\*\/%\(\)]+)$",
        )
        for pattern in patterns:
            if match := re.search(pattern, text):
                candidate = match.group(1).strip(" ?")
                if IntentRouter._looks_like_math(candidate):
                    return candidate
        return None

    @staticmethod
    def _looks_like_math(candidate: str) -> bool:
        math_terms = ("plus", "minus", "times", "multiplied", "divided", "over", "mod", "modulo", "power")
        if any(term in candidate for term in math_terms):
            return True
        return bool(re.fullmatch(r"[-\d\s\.\+\*\/%\(\)]+", candidate))
