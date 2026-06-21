from __future__ import annotations

import logging

from .actions import ActionExecutor
from .assistant import DesktopAssistant
from .config import Settings
from .history import HistoryEvent, HistoryRecorder
from .hud import FloatingHud
from .intent_router import IntentRouter
from .llm import OllamaAssistant
from .logging_utils import configure_logging
from .archive import AssistantArchive
from .embeddings import EmbeddingService
from .research import WebResearcher
from .speech import MissingSpeechToText, MissingTextToSpeech, SpeechToText, TextToSpeech
from .tray import TrayApplication
from .weather import WeatherService
from .models import RuntimeState


def main() -> None:
    log_path = configure_logging()
    logging.getLogger(__name__).info("Logging to %s", log_path)

    settings = Settings.load()
    router = IntentRouter()
    actions = ActionExecutor(settings)
    hud = FloatingHud(settings) if settings.hud_enabled else None
    history = HistoryRecorder()
    if hud:
        history.subscribe(hud.on_history_event)
    history.append(
        HistoryEvent(
            kind="app_started",
            data={
                "wake_word_enabled": settings.wake_word_enabled,
                "wake_word_phrase": settings.wake_word_phrase,
                "ollama_model": settings.ollama_model,
                "default_location": settings.default_location,
            },
            summary="Desktop voice assistant process started.",
        )
    )
    try:
        tts = TextToSpeech(settings)
    except Exception as exc:
        logging.getLogger(__name__).warning("Text-to-speech unavailable: %s", exc)
        tts = MissingTextToSpeech(str(exc))
    llm = OllamaAssistant(settings.ollama_model)
    archive = AssistantArchive()
    embedder = EmbeddingService(settings.embedding_model) if settings.semantic_retrieval_enabled else None
    assistant = None
    researcher = WebResearcher(
        llm,
        archive,
        fetch_limit=settings.web_fetch_limit,
        embedder=embedder,
        on_state_change=lambda state, reason: assistant.set_runtime_state(state, reason=reason) if assistant else None,
    )
    try:
        stt = SpeechToText(settings)
    except Exception as exc:
        logging.getLogger(__name__).warning("Speech-to-text unavailable: %s", exc)
        stt = MissingSpeechToText(str(exc))
    weather = WeatherService(settings.default_location)
    assistant = DesktopAssistant(settings, router, actions, stt, tts, llm, weather, history, researcher, hud=hud)
    assistant.set_runtime_state(RuntimeState.IDLE, reason="assistant boot complete")
    tray = TrayApplication(assistant, settings, hud=hud)
    if hud:
        hud.on_submit_text = tray.submit_text_request
    tray.run()


if __name__ == "__main__":
    main()
