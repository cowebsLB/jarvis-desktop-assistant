from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path


APP_DIR = Path.home() / ".desktop_voice_assistant"
SETTINGS_PATH = APP_DIR / "settings.json"
SUPPORTED_WAKE_WORDS = {"alexa", "hey jarvis", "hey mycroft", "hey rhasspy", "timer", "weather"}


@dataclass
class Settings:
    microphone_device: str | None = None
    wake_word_enabled: bool = True
    wake_word_phrase: str = "hey jarvis"
    stt_model_name: str = "base.en"
    stt_device: str = "cpu"
    stt_compute_type: str = "int8"
    ollama_model: str = "qwen2.5-coder:1.5B"
    embedding_model: str = "nomic-embed-text"
    tts_voice_id: str | None = None
    assistant_name: str = "Jarvis"
    assistant_style: str = "stark-butler"
    speech_rate: int = 185
    default_location: str = "Beirut, Lebanon"
    web_search_enabled: bool = True
    web_fetch_limit: int = 3
    web_archive_enabled: bool = True
    web_open_after_answer: bool = False
    archive_recall_limit: int = 3
    semantic_retrieval_enabled: bool = True
    conversation_followup_seconds: int = 45
    request_max_seconds: float = 8.0
    request_min_seconds: float = 1.5
    silence_timeout_seconds: float = 1.0
    speech_level_threshold: int = 450
    wake_cue_enabled: bool = True
    app_allowlist: dict[str, str] = field(
        default_factory=lambda: {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "settings": "ms-settings:",
            "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        }
    )
    site_allowlist: dict[str, str] = field(
        default_factory=lambda: {
            "youtube": "https://www.youtube.com",
            "gmail": "https://mail.google.com",
            "google": "https://www.google.com",
        }
    )
    log_retention: int = 100

    @classmethod
    def load(cls, path: Path = SETTINGS_PATH) -> "Settings":
        APP_DIR.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            settings = cls()
            settings.save(path)
            return settings

        data = json.loads(path.read_text(encoding="utf-8"))
        defaults = cls()
        merged = asdict(defaults)
        valid_keys = {item.name for item in fields(cls)}
        merged.update({key: value for key, value in data.items() if key in valid_keys})
        settings = cls(**merged)
        if settings.wake_word_phrase.lower() not in SUPPORTED_WAKE_WORDS:
            settings.wake_word_phrase = "hey jarvis"
        if settings.ollama_model == "qwen2.5:1.5b-instruct":
            settings.ollama_model = defaults.ollama_model
        if data.get("stt_model_path") and "stt_model_name" not in data:
            settings.stt_model_name = defaults.stt_model_name
        settings.save(path)
        return settings

    def save(self, path: Path = SETTINGS_PATH) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
