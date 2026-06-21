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
    def __init__(self, assistant: DesktopAssistant, settings: Settings, hud=None) -> None:
        self.assistant = assistant
        self.settings = settings
        self.hud = hud
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
            pystray.MenuItem(
                "HUD overlay enabled", self._toggle_hud, checked=lambda item: self.settings.hud_enabled
            ),
            pystray.MenuItem("Settings Panel", self._open_settings_ui),
            pystray.MenuItem("Open settings file", self._open_settings),
            pystray.MenuItem("Quit", self._quit),
        )
        self.wake_word_listener = WakeWordListener(settings, self.trigger_listen)

    def run(self) -> None:
        if self.hud:
            self.hud.start()
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
        if self.hud:
            self.hud.wake_detected()
        threading.Thread(target=self._handle_request, daemon=True, name="assistant-request").start()

    def submit_text_request(self, text: str) -> None:
        payload = text.strip()
        if not payload:
            return
        with self._request_lock:
            if self._request_active:
                LOGGER.info("Ignoring HUD text input because a request is already active")
                return
            self._request_active = True
        threading.Thread(
            target=self._handle_request,
            kwargs={"text_input": payload},
            daemon=True,
            name="assistant-text-request",
        ).start()

    def _handle_request(self, text_input: str | None = None) -> None:
        self.wake_word_listener.stop()
        if text_input is None:
            self.assistant.tts.play_listen_cue()
            self.assistant.set_runtime_state(RuntimeState.CAPTURING_COMMAND, reason="request capture started")
        self._refresh_title()
        try:
            result = self.assistant.handle_text_input(text_input) if text_input is not None else self.assistant.listen_and_handle()
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
            
            # Preserve waiting states so they display in HUD and wait for follow-up turns
            current_state = self.assistant.runtime_state
            should_transition = current_state not in {
                RuntimeState.AWAITING_CONFIRMATION,
                RuntimeState.CLARIFYING,
                RuntimeState.AWAITING_FOLLOWUP
            }
            
            if self.settings.wake_word_enabled:
                self.wake_word_listener.start()
                if should_transition:
                    self.assistant.set_runtime_state(RuntimeState.WAKE_LISTENING, reason="wake word listener resumed")
            else:
                if should_transition:
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

    def _toggle_hud(self, icon, item) -> None:
        self.settings.hud_enabled = not self.settings.hud_enabled
        self.settings.save()
        if self.settings.hud_enabled:
            if not self.hud:
                from .hud import FloatingHud
                self.hud = FloatingHud(self.settings)
                self.hud.on_submit_text = self.submit_text_request
                self.assistant.hud = self.hud
                self.assistant.history.subscribe(self.hud.on_history_event)
            self.hud.start()
        else:
            if self.hud:
                self.hud.stop()

    def _open_settings_ui(self, icon, item) -> None:
        if self.hud and self.hud.root and self.hud.thread and self.hud.thread.is_alive():
            self.hud.queue.put(self._launch_settings_on_hud)
        else:
            threading.Thread(target=self._launch_settings_standalone, daemon=True, name="settings-ui-thread").start()

    def _launch_settings_on_hud(self) -> None:
        if self.hud and self.hud.root:
            from .settings_ui import SettingsPanel
            import tkinter as tk
            SettingsPanel(tk.Toplevel(self.hud.root), self.settings, on_save=self._on_settings_saved)

    def _launch_settings_standalone(self) -> None:
        import tkinter as tk
        from .settings_ui import SettingsPanel
        root = tk.Tk()
        panel = SettingsPanel(root, self.settings, on_save=self._on_settings_saved)
        panel.window.protocol("WM_DELETE_WINDOW", root.destroy)
        root.mainloop()

    def _on_settings_saved(self) -> None:
        LOGGER.info("Settings saved via GUI panel, synchronizing runtime state...")
        # Sync wake word
        if self.settings.wake_word_enabled:
            self.wake_word_listener.start()
            self.assistant.set_runtime_state(RuntimeState.WAKE_LISTENING, reason="settings sync: wake word active")
        else:
            self.wake_word_listener.stop()
            self.assistant.set_runtime_state(RuntimeState.IDLE, reason="settings sync: wake word disabled")

        # Sync HUD
        if self.settings.hud_enabled:
            if not self.hud:
                from .hud import FloatingHud
                self.hud = FloatingHud(self.settings)
                self.hud.on_submit_text = self.submit_text_request
                self.assistant.hud = self.hud
                self.assistant.history.subscribe(self.hud.on_history_event)
            self.hud.start()
        else:
            if self.hud:
                self.hud.stop()

        # Update speech rate for TTS if supported
        self.assistant.settings = self.settings
        if hasattr(self.assistant.tts, "engine") and self.assistant.tts.engine:
            try:
                self.assistant.tts.engine.setProperty("rate", self.settings.speech_rate)
            except Exception:
                pass
        self._refresh_title()

    def _open_settings(self, icon, item) -> None:
        Path(SETTINGS_PATH).touch(exist_ok=True)
        import os

        os.startfile(SETTINGS_PATH)  # type: ignore[attr-defined]

    def _quit(self, icon, item) -> None:
        self.wake_word_listener.stop()
        if self.hud:
            self.hud.stop()
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
