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
from .speech import WakeWordListener, TextToSpeech, MissingTextToSpeech


import ctypes
import time
try:
    from ctypes import wintypes
except ImportError:
    wintypes = None  # type: ignore

LOGGER = logging.getLogger(__name__)

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
VK_J = 0x4A
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

user32 = None
kernel32 = None
if wintypes is not None:
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        
        # Set up prototypes
        user32.RegisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT)
        user32.RegisterHotKey.restype = wintypes.BOOL
        
        user32.UnregisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int)
        user32.UnregisterHotKey.restype = wintypes.BOOL
        
        user32.GetMessageW.argtypes = (ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT)
        user32.GetMessageW.restype = wintypes.BOOL
        
        user32.PostThreadMessageW.argtypes = (wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
        user32.PostThreadMessageW.restype = wintypes.BOOL
    except Exception:
        pass


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
        self._ptt_thread_id = None

    def run(self) -> None:
        if self.hud:
            self.hud.start()
        self._sync_listeners(reason="app run")
        self.icon.run()

    def _sync_listeners(self, reason: str = "sync") -> None:
        if self.settings.push_to_talk_enabled:
            self.wake_word_listener.stop()
            self._start_ptt_listener()
            if self.assistant.runtime_state == RuntimeState.WAKE_LISTENING:
                self.assistant.set_runtime_state(RuntimeState.IDLE, reason=f"{reason}: PTT active")
        else:
            self._stop_ptt_listener()
            if self.settings.wake_word_enabled:
                self.wake_word_listener.start()
                if self.wake_word_listener.ready and self.assistant.runtime_state == RuntimeState.IDLE:
                    self.assistant.set_runtime_state(RuntimeState.WAKE_LISTENING, reason=f"{reason}: wake word active")
            else:
                self.wake_word_listener.stop()
                if self.assistant.runtime_state == RuntimeState.WAKE_LISTENING:
                    self.assistant.set_runtime_state(RuntimeState.IDLE, reason=f"{reason}: wake word disabled")

    def _run_ptt_hotkey(self) -> None:
        if user32 is None or kernel32 is None or wintypes is None:
            LOGGER.warning("PTT global hotkey is not supported on this platform/configuration")
            return

        self._ptt_thread_id = kernel32.GetCurrentThreadId()
        hotkey_id = 99  # A unique ID for this hotkey
        
        # Register Ctrl+Alt+J
        success = user32.RegisterHotKey(None, hotkey_id, MOD_CONTROL | MOD_ALT, VK_J)
        if not success:
            LOGGER.error("Failed to register PTT global hotkey Ctrl+Alt+J. Error code: %s", ctypes.GetLastError())
            self._ptt_thread_id = None
            return

        LOGGER.info("PTT global hotkey Ctrl+Alt+J registered successfully")
        
        msg = wintypes.MSG()
        try:
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                if msg.message == WM_HOTKEY:
                    if msg.wParam == hotkey_id:
                        LOGGER.info("PTT hotkey Ctrl+Alt+J pressed, triggering listen")
                        self.trigger_listen()
        finally:
            user32.UnregisterHotKey(None, hotkey_id)
            LOGGER.info("PTT global hotkey unregistered")
            self._ptt_thread_id = None

    def _start_ptt_listener(self) -> None:
        if self._ptt_thread_id is not None:
            return  # Already running
        threading.Thread(target=self._run_ptt_hotkey, daemon=True, name="ptt-hotkey").start()

    def _stop_ptt_listener(self) -> None:
        if self._ptt_thread_id is not None and user32 is not None:
            user32.PostThreadMessageW(self._ptt_thread_id, WM_QUIT, 0, 0)

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
        result = None
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
            
            # Determine if we should auto-trigger voice follow-up
            is_followup = (
                text_input is None
                and result is not None
                and (result.success or self.assistant.runtime_state in {RuntimeState.AWAITING_CONFIRMATION, RuntimeState.CLARIFYING})
                and self.assistant.runtime_state in {
                    RuntimeState.AWAITING_CONFIRMATION,
                    RuntimeState.CLARIFYING,
                    RuntimeState.AWAITING_FOLLOWUP
                }
            )
            
            if is_followup:
                # Do not transition or start wake word listener; trigger next listen directly
                self._refresh_title()
                self.trigger_listen()
            else:
                # If the follow-up had no speech or failed, reset state to idle/wake listening
                if result is None or not result.success:
                    current_state = self.assistant.runtime_state
                    if current_state in {RuntimeState.AWAITING_CONFIRMATION, RuntimeState.CLARIFYING, RuntimeState.AWAITING_FOLLOWUP}:
                        if self.settings.wake_word_enabled and not self.settings.push_to_talk_enabled:
                            self.assistant.set_runtime_state(RuntimeState.WAKE_LISTENING, reason="follow-up cycle reset")
                        else:
                            self.assistant.set_runtime_state(RuntimeState.IDLE, reason="follow-up cycle reset")
                
                current_state = self.assistant.runtime_state
                should_transition = current_state not in {
                    RuntimeState.AWAITING_CONFIRMATION,
                    RuntimeState.CLARIFYING,
                    RuntimeState.AWAITING_FOLLOWUP
                }
                
                if self.settings.wake_word_enabled and not self.settings.push_to_talk_enabled:
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
        self._sync_listeners(reason="toggle wake word")
        self._refresh_title()

    def _toggle_hud(self, icon, item) -> None:
        self.settings.hud_enabled = not self.settings.hud_enabled
        self.settings.save()
        if self.hud:
            self.hud.set_enabled(self.settings.hud_enabled)

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
        self._sync_listeners(reason="settings sync")

        # Sync HUD
        if self.hud:
            self.hud.set_enabled(self.settings.hud_enabled)

        # Sync assistant runtime configuration
        self.assistant.settings = self.settings
        self.assistant.session.followup_seconds = self.settings.conversation_followup_seconds
        if hasattr(self.assistant.llm, "update_settings"):
            self.assistant.llm.update_settings(
                model=self.settings.ollama_model,
                assistant_name=self.settings.assistant_name,
                assistant_style=self.settings.assistant_style,
                remote_model=self.settings.gemini_model,
            )
        if self.assistant.researcher:
            self.assistant.researcher.fetch_limit = self.settings.web_fetch_limit
            self.assistant.researcher.archive_enabled = self.settings.web_archive_enabled
        
        # Sync TTS engine
        if self.settings.tts_engine == "none":
            self.assistant.tts = MissingTextToSpeech("Disabled in settings")
        else:
            try:
                self.assistant.tts = TextToSpeech(self.settings)
            except Exception as exc:
                LOGGER.warning("Failed to recreate Text-to-Speech: %s", exc)
                self.assistant.tts = MissingTextToSpeech(str(exc))
        self._refresh_title()

    def _open_settings(self, icon, item) -> None:
        Path(SETTINGS_PATH).touch(exist_ok=True)
        import os

        os.startfile(SETTINGS_PATH)  # type: ignore[attr-defined]

    def _quit(self, icon, item) -> None:
        self.wake_word_listener.stop()
        self._stop_ptt_listener()
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
            if self.settings.wake_word_enabled and not self.settings.push_to_talk_enabled:
                self.assistant.set_runtime_state(RuntimeState.WAKE_LISTENING, reason="speech model warmup complete")
                self.wake_word_listener.start()
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
