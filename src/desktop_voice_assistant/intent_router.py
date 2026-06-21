from __future__ import annotations

import re

from .models import IntentResult


class IntentRouter:
    def route(self, transcript: str) -> IntentResult:
        text = transcript.strip()
        normalized = self._normalize_text(text)

        # Power action, delete file, send email (risky actions)
        if match := re.search(r"\b(shutdown|restart|sleep)\s+(?:the\s+)?(?:system|computer|machine|pc)\b", normalized):
            return IntentResult("power_action", 0.95, {"action": match.group(1)})
        if match := re.search(r"\b(?:delete|remove)\s+file\s+(.+)$", normalized):
            orig_match = re.search(r"\b(?:delete|remove)\s+file\s+(.+)$", text, re.IGNORECASE)
            target = orig_match.group(1).strip("?.!, ") if orig_match else match.group(1).strip()
            return IntentResult("delete_file", 0.95, {"target": target})
        if match := re.search(r"\b(?:delete|remove)\s+([\w\-\.\\\/:\s\(\)]+\.\w{2,5})$", normalized):
            orig_match = re.search(r"\b(?:delete|remove)\s+(.+)$", text, re.IGNORECASE)
            target = orig_match.group(1).strip("?.!, ") if orig_match else match.group(1).strip()
            if not any(x in target.lower() for x in ("all ", "my ", "the ", "alarm", "timer", "task", "reminder", "folder", "directory")):
                return IntentResult("delete_file", 0.95, {"target": target})
        if match := re.search(r"\bsend\s+email\s+to\s+([\w\-\.\+]+@[\w\-\.]+)\b", text, re.IGNORECASE):
            return IntentResult("send_email", 0.95, {"to": match.group(1)})

        # Clear timers/reminders/alarms
        if re.search(r"\b(?:clear|remove|delete|cancel)\s+(?:all\s+|the\s+|my\s+)*(?:timer|timers)\b", normalized):
            return IntentResult("clear_timers", 0.95, {})
        if re.search(r"\b(?:clear|remove|delete|cancel)\s+(?:all\s+|the\s+|my\s+)*(?:reminder|reminders)\b", normalized):
            return IntentResult("clear_reminders", 0.95, {})
        if re.search(r"\b(?:clear|remove|delete|cancel)\s+(?:all\s+|the\s+|my\s+)*(?:alarm|alarms)\b", normalized):
            return IntentResult("clear_alarms", 0.95, {})

        # Timers
        if match := re.search(r"\b(?:set|start)?\s*(?:a)?\s*timer\s+(?:for\s+)?(\d+)\s*(second|sec|minute|min|hour|hr)s?\b", normalized):
            if not any(word in normalized for word in ("remove", "delete", "clear", "cancel")):
                return IntentResult("set_timer", 0.95, {"duration": match.group(1), "unit": match.group(2)})

        # Reminders
        if match := re.search(r"\b(?:set\s+a\s+)?reminder\s+(?:to\s+|for\s+)?(.+?)\s+in\s+(\d+)\s*(second|sec|minute|min|hour|hr)s?\b", normalized):
            if not any(word in normalized for word in ("remove", "delete", "clear", "cancel")):
                return IntentResult("set_reminder", 0.95, {"text": match.group(1).strip(), "duration": match.group(2), "unit": match.group(3)})
        if match := re.search(r"\bremind\s+me\s+to\s+(.+?)\s+in\s+(\d+)\s*(second|sec|minute|min|hour|hr)s?\b", normalized):
            if not any(word in normalized for word in ("remove", "delete", "clear", "cancel")):
                return IntentResult("set_reminder", 0.95, {"text": match.group(1).strip(), "duration": match.group(2), "unit": match.group(3)})

        # Alarms
        if match := re.search(r"\b(?:set\s+an\s+)?alarm\s+(?:for\s+)?(\d{1,2}):(\d{2})\s*(am|pm)?\b", normalized):
            if not any(word in normalized for word in ("remove", "delete", "clear", "cancel")):
                return IntentResult("set_alarm", 0.95, {"hour": match.group(1), "minute": match.group(2), "period": match.group(3) or ""})
        if match := re.search(r"\b(?:set\s+an\s+)?alarm\s+(?:for\s+)?(\d{1,2})\s*(am|pm)\b", normalized):
            if not any(word in normalized for word in ("remove", "delete", "clear", "cancel")):
                return IntentResult("set_alarm", 0.95, {"hour": match.group(1), "minute": "00", "period": match.group(2)})

        # Tasks
        if match := re.search(r"\badd\s+(.+?)\s+to\s+(?:my\s+)?(?:task\s+list|tasks)\b", normalized):
            return IntentResult("add_task", 0.95, {"task": match.group(1).strip()})

        if re.search(r"\b(?:list|show|what are)\s+(?:my\s+)?(?:tasks|task\s+list)\b", normalized):
            return IntentResult("list_tasks", 0.95, {})

        if re.search(r"\b(?:clear|empty|delete)\s+(?:my\s+)?(?:tasks|task\s+list)\b", normalized):
            return IntentResult("clear_tasks", 0.95, {})

        # Quick notes
        if match := re.search(r"\b(?:take\s+a\s+note\s+that|save\s+note|add\s+note\s+that|take\s+note)\s+(.+)$", normalized):
            return IntentResult("take_note", 0.95, {"text": match.group(1).strip()})

        # Browser Automation
        if re.search(r"\b(?:summarize|explain)\s+(?:this|the)\s+(?:page|website|webpage)\b", normalized):
            return IntentResult("browser_summarize", 0.95, {})

        if re.search(r"\b(?:next|switch\s+to\s+next)\s+tab\b", normalized):
            return IntentResult("browser_tab_next", 0.95, {})

        if re.search(r"\b(?:previous|last|switch\s+to\s+previous)\s+tab\b", normalized):
            return IntentResult("browser_tab_prev", 0.95, {})

        if re.search(r"\b(?:open\s+(?:a\s+)?new|new)\s+tab\b", normalized):
            return IntentResult("browser_tab_new", 0.95, {})

        if re.search(r"\bclose\s+(?:this\s+)?tab\b", normalized):
            return IntentResult("browser_tab_close", 0.95, {})

        if re.search(r"\bgo\s+back\b", normalized):
            return IntentResult("browser_back", 0.95, {})

        if re.search(r"\bgo\s+forward\b", normalized):
            return IntentResult("browser_forward", 0.95, {})

        if re.search(r"\b(?:refresh|reload)\s+(?:this\s+)?page\b", normalized):
            return IntentResult("browser_refresh", 0.95, {})

        # Notepad Write & Save
        if match := re.search(r"\b(?:write|save)\s+(.+?)\s+in\s+notepad\s+and\s+save\s+as\s+(.+)\b", normalized):
            return IntentResult("notepad_write_and_save", 0.95, {"text": match.group(1).strip(), "filename": match.group(2).strip()})
        if match := re.search(r"\b(?:write|save)\s+(.+?)\s+and\s+save\s+as\s+(.+?)\s+in\s+notepad\b", normalized):
            return IntentResult("notepad_write_and_save", 0.95, {"text": match.group(1).strip(), "filename": match.group(2).strip()})
        if match := re.search(r"\bwrite\s+and\s+save\s+(.+?)\s+as\s+(.+?)\s+in\s+notepad\b", normalized):
            return IntentResult("notepad_write_and_save", 0.95, {"text": match.group(1).strip(), "filename": match.group(2).strip()})
        if match := re.search(r"\bopen\s+notepad\s+and\s+(?:type|write)\s+(.+?)(?:\s+in\s+it)?$", normalized):
            return IntentResult("notepad_write_and_save", 0.95, {"text": match.group(1).strip(), "filename": "notes.txt"})
        if match := re.search(r"\b(?:type|write)\s+(.+?)\s+in\s+notepad(?:\s+and\s+save)?$", normalized):
            return IntentResult("notepad_write_and_save", 0.95, {"text": match.group(1).strip(), "filename": "notes.txt"})

        # Browser Search and Bookmark
        if match := re.search(r"\bsearch\s+(?:the\s+)?(?:browser|web|internet)\s+for\s+(.+?)\s+and\s+bookmark\s*(?:the\s+)?(?:page|it)?\b", normalized):
            return IntentResult("browser_search_and_bookmark", 0.95, {"query": match.group(1).strip()})
        if match := re.search(r"\bsearch\s+(?:for\s+)?(.+?)\s+and\s+bookmark\s+(?:the\s+)?(?:page|it)\b", normalized):
            return IntentResult("browser_search_and_bookmark", 0.95, {"query": match.group(1).strip()})
        if match := re.search(r"\bsearch\s+and\s+bookmark\s+(.+)\b", normalized):
            return IntentResult("browser_search_and_bookmark", 0.95, {"query": match.group(1).strip()})

        # VSCode Open Terminal
        if re.search(r"\bopen\s+(?:the\s+)?terminal\s+(?:pane\s+)?in\s+(?:vscode|visual\s+studio\s+code)\b", normalized) or re.search(r"\bopen\s+(?:vscode|visual\s+studio\s+code)\s+terminal\b", normalized):
            return IntentResult("vscode_open_terminal", 0.95, {})

        # UI Controls / Coordinate Actions
        if match := re.search(r"\bdouble\s+click\s+(?:at\s+|coordinate\s+|on\s+)*(?:x\s*)?(\d+)[,\s]+(?:y\s*)?(\d+)\b", normalized):
            return IntentResult("ui_double_click_coordinate", 0.95, {"x": match.group(1), "y": match.group(2)})
        if match := re.search(r"\bclick\s+(?:at\s+|coordinate\s+|on\s+)*(?:x\s*)?(\d+)[,\s]+(?:y\s*)?(\d+)\b", normalized):
            return IntentResult("ui_click_coordinate", 0.95, {"x": match.group(1), "y": match.group(2)})
        if match := re.search(r"\b(?:write|type)\s+(.+?)\s+(?:at|on|coordinate)\s+(?:x\s*)?(\d+)[,\s]+(?:y\s*)?(\d+)\b", normalized):
            return IntentResult("ui_write_at_coordinate", 0.95, {"text": match.group(1).strip(), "x": match.group(2), "y": match.group(3)})
        # Browser click control / fill form (must be before ui_click_control to avoid 'sign in' ambiguity)
        if match := re.search(r"\bclick\s+(?:the\s+)?(.+?)\s+(?:button|link|tab|control)\s+(?:on|in)\s+(?:the\s+)?(?:browser|page|website)\b", normalized):
            return IntentResult("browser_click_control", 0.9, {"control_name": match.group(1).strip()})
        if match := re.search(r"\bfill\s+(?:the\s+)?(?:form|field)\s+(.+?)\s+(?:in|on)\s+(?:the\s+)?(?:browser|page)\b", normalized):
            return IntentResult("browser_fill_form", 0.9, {"data": match.group(1).strip()})

        if match := re.search(r"\bclick\s+(?:button\s+)?(.+?)\s+in\s+(.+)\b", normalized):
            return IntentResult("ui_click_control", 0.95, {"control_name": match.group(1).strip(), "window_title": match.group(2).strip()})

        # Spotify controls
        if re.search(r"\b(?:pause|resume|play\s+pause|toggle\s+playback)\s+(?:spotify|music|song)\b", normalized) or normalized in {"pause spotify", "play spotify", "pause music", "resume music", "play pause"}:
            return IntentResult("spotify_play_pause", 0.95, {})
        if re.search(r"\b(?:next|skip)\s+(?:song|track)\b", normalized) or normalized in {"next song", "next track", "skip track", "skip song"}:
            return IntentResult("spotify_next_track", 0.95, {})
        if re.search(r"\b(?:previous|last|prev)\s+(?:song|track)\b", normalized) or normalized in {"previous song", "previous track", "last song"}:
            return IntentResult("spotify_prev_track", 0.95, {})
        if re.search(r"\b(?:volume\s+up|increase\s+volume|louder)\s+(?:spotify|music)?\b", normalized) or normalized in {"volume up", "louder", "turn up spotify"}:
            return IntentResult("spotify_volume_up", 0.95, {})
        if re.search(r"\b(?:volume\s+down|decrease\s+volume|quieter)\s+(?:spotify|music)?\b", normalized) or normalized in {"volume down", "quieter", "turn down spotify"}:
            return IntentResult("spotify_volume_down", 0.95, {})

        # Discord controls
        if re.search(r"\b(?:mute|unmute)\s+(?:discord|microphone|mic)\b", normalized) or normalized in {"discord mute", "toggle mute"}:
            return IntentResult("discord_mute", 0.95, {})
        if re.search(r"\b(?:deafen|undeafen)\s+(?:discord)?\b", normalized) or normalized in {"deafen discord", "undeafen discord"}:
            return IntentResult("discord_deafen", 0.95, {})
        if match := re.search(r"\b(?:go to|navigate to|open)\s+(?:discord\s+)?(?:channel|server|user|dm)\s+(.+)$", normalized):
            return IntentResult("discord_navigate", 0.95, {"target": match.group(1).strip()})

        # Slack controls
        if re.search(r"\b(?:mute|unmute)\s+slack\b", normalized) or normalized in {"mute slack", "unmute slack", "slack mute"}:
            return IntentResult("slack_mute", 0.95, {})
        if match := re.search(r"\b(?:go to|navigate to|open)\s+(?:slack\s+)?(?:channel|user|dm)\s+(.+)$", normalized):
            return IntentResult("slack_navigate", 0.95, {"target": match.group(1).strip()})

        if match := re.match(r"^(type|dictate)\s+(.+)$", normalized, re.IGNORECASE):
            dictated_text = self._extract_after_command(text, match.group(1))
            return IntentResult("dictate", 0.99, {"text": dictated_text})

        if self._is_clipboard_copy_request(normalized):
            return IntentResult("clipboard_copy", 0.95, {})

        if self._is_clipboard_paste_request(normalized):
            return IntentResult("clipboard_paste", 0.95, {})

        if self._is_clipboard_read_request(normalized):
            return IntentResult("clipboard_read", 0.95, {})

        if self._is_clipboard_save_request(normalized):
            return IntentResult("clipboard_save_note", 0.95, {})

        if direction := self._extract_window_switch_direction(normalized):
            return IntentResult("switch_window", 0.95, {"direction": direction})

        if focus_target := self._extract_focus_target(normalized):
            return IntentResult("focus_target", 0.94, {"target": focus_target})

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
        normalized = re.sub(r"[,\.!\?]+", " ", normalized)
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
        extracted = match.group(1).strip(" ,.!?")
        extracted = re.sub(r"\b(please|for me|right now)\b", "", extracted, flags=re.IGNORECASE)
        return re.sub(r"\s+", " ", extracted).strip(" ,.!?")

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

    @staticmethod
    def _extract_window_switch_direction(text: str) -> str | None:
        next_commands = {
            "next window",
            "switch window",
            "switch to next window",
            "focus next window",
        }
        previous_commands = {
            "previous window",
            "last window",
            "switch to previous window",
            "focus previous window",
            "switch back",
        }
        if text in next_commands:
            return "next"
        if text in previous_commands:
            return "previous"
        return None

    @staticmethod
    def _extract_focus_target(text: str) -> str | None:
        patterns = (
            r"^(?:focus on|switch to|bring up)\s+(.+)$",
            r"^(?:focus|activate)\s+(.+)$",
        )
        for pattern in patterns:
            if match := re.search(pattern, text):
                candidate = match.group(1).strip()
                if candidate not in {"next window", "previous window", "last window"}:
                    return candidate
        return None

    @staticmethod
    def _is_clipboard_copy_request(text: str) -> bool:
        return text in {
            "copy that",
            "copy this",
            "copy selection",
            "copy the selection",
            "copy selected text",
        }

    @staticmethod
    def _is_clipboard_paste_request(text: str) -> bool:
        return text in {
            "paste",
            "paste that",
            "paste it",
            "paste clipboard",
            "paste the clipboard",
        }

    @staticmethod
    def _is_clipboard_read_request(text: str) -> bool:
        return text in {
            "read clipboard",
            "read the clipboard",
            "what is on my clipboard",
            "whats on my clipboard",
            "what's on my clipboard",
        }

    @staticmethod
    def _is_clipboard_save_request(text: str) -> bool:
        return text in {
            "save clipboard to note",
            "save the clipboard to note",
            "save clipboard as note",
            "save this clipboard to note",
        }
