from __future__ import annotations

import logging
import threading
from pathlib import Path

from PIL import Image, ImageDraw
import pystray

from .assistant import DesktopAssistant
from .config import SETTINGS_PATH, Settings
from .model_manager import ModelManager
from .models import RuntimeState
from .speech import WakeWordListener


LOGGER = logging.getLogger(__name__)


class TrayApplication:
    def __init__(self, assistant: DesktopAssistant, settings: Settings) -> None:
        self.assistant = assistant
        self.settings = settings
        self.model_manager = ModelManager(settings)
        self._request_lock = threading.Lock()
        self._request_active = False
        self.icon = pystray.Icon("desktop-voice-assistant")
        self.icon.icon = self._create_icon()
        self.icon.title = self._title()
        self.icon.menu = pystray.Menu(
            pystray.MenuItem("Listen now", self._listen_now),
            pystray.MenuItem("Warm speech model", self._install_speech_model),
            pystray.MenuItem(
                "Wake word enabled", self._toggle_wake_word, checked=lambda item: self.settings.wake_word_enabled
            ),
            pystray.MenuItem("Open settings file", self._open_settings),
            pystray.MenuItem("Quit", self._quit),
        )
        self.wake_word_listener = WakeWordListener(settings, self.trigger_listen)

    def run(self) -> None:
        if self.settings.wake_word_enabled:
            self.wake_word_listener.start()
            if self.wake_word_listener.ready:
                self.assistant.set_runtime_state(RuntimeState.WAKE_LISTENING, reason="wake word listener ready")
                self._refresh_title()
        self.icon.run()

    def trigger_listen(self) -> None:
        with self._request_lock:
            if self._request_active:
                LOGGER.info("Ignoring listen trigger because a request is already active")
                return
            self._request_active = True
        threading.Thread(target=self._handle_request, daemon=True, name="assistant-request").start()

    def _handle_request(self) -> None:
        self.wake_word_listener.stop()
        self.assistant.tts.play_listen_cue()
        self.assistant.set_runtime_state(RuntimeState.CAPTURING_COMMAND, reason="request capture started")
        self._refresh_title()
        try:
            result = self.assistant.listen_and_handle()
            LOGGER.info("Assistant result: success=%s message=%s", result.success, result.message)
            self._refresh_title()
        except Exception as exc:  # pragma: no cover - runtime integration issue
            LOGGER.exception("Assistant request failed")
            self.assistant.set_runtime_state(RuntimeState.ERROR, reason="tray request handler failure")
            self._refresh_title()
            self.assistant.tts.speak(f"Something went wrong: {exc}")
        finally:
            with self._request_lock:
                self._request_active = False
            if self.settings.wake_word_enabled:
                self.wake_word_listener.start()
                self.assistant.set_runtime_state(RuntimeState.WAKE_LISTENING, reason="wake word listener resumed")
            else:
                self.assistant.set_runtime_state(RuntimeState.IDLE, reason="request cycle completed")
            self._refresh_title()

    def _listen_now(self, icon, item) -> None:
        self.trigger_listen()

    def _install_speech_model(self, icon, item) -> None:
        threading.Thread(target=self._install_speech_model_worker, daemon=True, name="install-speech-model").start()

    def _toggle_wake_word(self, icon, item) -> None:
        self.settings.wake_word_enabled = not self.settings.wake_word_enabled
        self.settings.save()
        if self.settings.wake_word_enabled:
            self.wake_word_listener.start()
            self.assistant.set_runtime_state(RuntimeState.WAKE_LISTENING, reason="wake word enabled")
        else:
            self.wake_word_listener.stop()
            self.assistant.set_runtime_state(RuntimeState.IDLE, reason="wake word disabled")
        self._refresh_title()

    def _open_settings(self, icon, item) -> None:
        Path(SETTINGS_PATH).touch(exist_ok=True)
        import os

        os.startfile(SETTINGS_PATH)  # type: ignore[attr-defined]

    def _quit(self, icon, item) -> None:
        self.wake_word_listener.stop()
        self.assistant.set_runtime_state(RuntimeState.SHUTTING_DOWN, reason="tray quit requested")
        self._refresh_title()
        self.icon.stop()

    def _install_speech_model_worker(self) -> None:
        self.assistant.set_runtime_state(RuntimeState.EXECUTING, reason="warming speech model")
        self._refresh_title()
        try:
            model_name = self.model_manager.install_stt_model()
            self.assistant.reload_stt()
            LOGGER.info("Speech model warmed: %s", model_name)
            self.assistant.tts.speak("Voice recognition is warmed up and ready.")
        except Exception as exc:  # pragma: no cover - runtime/network issue
            LOGGER.exception("Speech model installation failed")
            self.assistant.disable_stt(f"Speech model warmup failed: {exc}")
            self.assistant.set_runtime_state(RuntimeState.ERROR, reason="speech model warmup failed")
            self.assistant.tts.speak("Speech model warmup failed.")
        finally:
            if self.settings.wake_word_enabled:
                self.assistant.set_runtime_state(RuntimeState.WAKE_LISTENING, reason="speech model warmup complete")
            else:
                self.assistant.set_runtime_state(RuntimeState.IDLE, reason="speech model warmup complete")
            self._refresh_title()

    def _refresh_title(self) -> None:
        self.icon.title = self._title()

    def _title(self) -> str:
        return f"Desktop Voice Assistant - {self.assistant.runtime_state.value.replace('_', ' ').title()}"

    @staticmethod
    def _create_icon() -> Image.Image:
        image = Image.new("RGB", (64, 64), color=(28, 35, 51))
        draw = ImageDraw.Draw(image)
        draw.ellipse((14, 6, 50, 42), fill=(223, 240, 255))
        draw.rectangle((28, 36, 36, 54), fill=(223, 240, 255))
        draw.rectangle((20, 52, 44, 56), fill=(223, 240, 255))
        return image
