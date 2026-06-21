from __future__ import annotations

import logging
import math
import queue
import threading
import time

import numpy as np

from .config import Settings
from .models import TranscriptResult


LOGGER = logging.getLogger(__name__)


def resolve_microphone_device(device_setting: str | int | None) -> int | str | None:
    if not device_setting or not isinstance(device_setting, str):
        return device_setting
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        for idx, d in enumerate(devices):
            if d.get("max_input_channels", 0) > 0 and d.get("name") == device_setting:
                return idx
        LOGGER.warning("Configured microphone '%s' was not found. Falling back to system default input.", device_setting)
    except Exception:
        pass
    return None

SUPPORTED_WAKE_WORDS = {
    "alexa": "alexa",
    "hey jarvis": "hey_jarvis",
    "hey mycroft": "hey_mycroft",
    "hey rhasspy": "hey_rhasspy",
    "timer": "timer",
    "weather": "weather",
}


class TextToSpeech:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        import pyttsx3

        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", settings.speech_rate)
        voice_id = settings.tts_voice_id or self._pick_default_voice()
        if voice_id:
            self.engine.setProperty("voice", voice_id)
        self._lock = threading.Lock()

    def speak(self, text: str) -> None:
        with self._lock:
            self.engine.say(text)
            self.engine.runAndWait()
            
            # Workaround for non-blocking TTS on background threads:
            # Sleep for the estimated duration of the speech plus padding
            rate = max(50, self.settings.speech_rate)
            word_count = len(text.split())
            duration = (word_count / rate) * 60.0
            time.sleep(duration + 0.6)

    def play_listen_cue(self) -> None:
        if not self.settings.wake_cue_enabled:
            return
        try:
            import winsound

            winsound.Beep(1046, 90)
            winsound.Beep(1318, 90)
        except Exception as exc:  # pragma: no cover - platform/runtime issue
            LOGGER.debug("Listen cue failed: %s", exc)

    def _pick_default_voice(self) -> str | None:
        try:
            voices = self.engine.getProperty("voices") or []
        except Exception as exc:  # pragma: no cover - engine/runtime issue
            LOGGER.debug("Unable to enumerate TTS voices: %s", exc)
            return None

        preferred_terms = ("zira", "hazel", "aria", "jenny", "female")
        for term in preferred_terms:
            for voice in voices:
                name = f"{getattr(voice, 'name', '')} {getattr(voice, 'id', '')}".lower()
                if term in name:
                    return getattr(voice, "id", None)

        return getattr(voices[0], "id", None) if voices else None


class MissingTextToSpeech:
    def __init__(self, reason: str) -> None:
        self.reason = reason

    def speak(self, text: str) -> None:
        LOGGER.warning("TTS unavailable: %s. Intended speech: %s", self.reason, text)

    def play_listen_cue(self) -> None:
        LOGGER.debug("Skipping listen cue because TTS/cue output is unavailable")


class SpeechToText:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        from faster_whisper import WhisperModel

        self.model = WhisperModel(
            settings.stt_model_name,
            device=settings.stt_device,
            compute_type=settings.stt_compute_type,
        )

    def transcribe_once(self, seconds: float | None = None, sample_rate: int = 16000) -> TranscriptResult:
        max_seconds = seconds or self.settings.request_max_seconds
        LOGGER.info(
            "Recording audio with adaptive stop max_seconds=%.1f silence_timeout=%.1f threshold=%s",
            max_seconds,
            self.settings.silence_timeout_seconds,
            self.settings.speech_level_threshold,
        )
        recording, audio_seconds, ended_early = self._record_until_silence(
            sample_rate=sample_rate,
            max_seconds=max_seconds,
            min_seconds=self.settings.request_min_seconds,
            silence_timeout=self.settings.silence_timeout_seconds,
            speech_threshold=self.settings.speech_level_threshold,
            input_device=resolve_microphone_device(self.settings.microphone_device),
        )
        if recording.size == 0:
            return TranscriptResult(text="", audio_seconds=audio_seconds, ended_early=ended_early)

        normalized = recording.reshape(-1).astype("float32") / 32768.0
        segments, _ = self.model.transcribe(
            normalized,
            language="en",
            beam_size=1,
            vad_filter=False,
            condition_on_previous_text=False,
        )
        text_parts = []
        confidence_sum = 0.0
        segment_count = 0
        for segment in segments:
            text_val = segment.text.strip()
            if text_val:
                text_parts.append(text_val)
                # avg_logprob is log probability of the segment tokens. Convert to 0..1 confidence.
                prob = math.exp(segment.avg_logprob) if hasattr(segment, "avg_logprob") else 1.0
                confidence_sum += prob
                segment_count += 1
        
        text = " ".join(text_parts).strip()
        confidence = (confidence_sum / segment_count) if segment_count > 0 else 1.0
        
        return TranscriptResult(
            text=text,
            audio_seconds=audio_seconds,
            ended_early=ended_early,
            confidence=confidence,
        )

    @staticmethod
    def _record_until_silence(
        *,
        sample_rate: int,
        max_seconds: float,
        min_seconds: float,
        silence_timeout: float,
        speech_threshold: int,
        input_device,
    ) -> tuple[np.ndarray, float, bool]:
        import sounddevice as sd

        blocksize = 1600
        chunks: list[np.ndarray] = []
        started_at = time.monotonic()
        speech_started = False
        last_loud_at = started_at
        ended_early = False
        audio_queue: queue.Queue = queue.Queue()

        def callback(indata, frames, time_info, status) -> None:
            if status:
                LOGGER.debug("Recording stream status: %s", status)
            audio_queue.put(indata.copy())

        with sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
            callback=callback,
            device=input_device,
            blocksize=blocksize,
        ):
            while True:
                elapsed = time.monotonic() - started_at
                if elapsed >= max_seconds:
                    break

                try:
                    chunk = audio_queue.get(timeout=0.2)
                except queue.Empty:
                    continue

                chunks.append(chunk)
                level = int(np.abs(chunk.astype(np.int32)).mean())
                now = time.monotonic()
                if level >= speech_threshold:
                    speech_started = True
                    last_loud_at = now

                if speech_started and elapsed >= min_seconds and (now - last_loud_at) >= silence_timeout:
                    ended_early = True
                    break

        if not chunks:
            return np.zeros((0, 1), dtype="int16"), 0.0, ended_early

        recording = np.concatenate(chunks, axis=0)
        audio_seconds = recording.shape[0] / sample_rate
        return recording, audio_seconds, ended_early


class MissingSpeechToText:
    def __init__(self, reason: str) -> None:
        self.reason = reason

    def transcribe_once(self, seconds: float = 6.0, sample_rate: int = 16000) -> TranscriptResult:
        raise RuntimeError(self.reason)


class WakeWordListener:
    def __init__(self, settings: Settings, on_detected) -> None:
        self.settings = settings
        self.on_detected = on_detected
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._ready = False

    @property
    def ready(self) -> bool:
        return self._ready

    def start(self) -> None:
        try:
            from openwakeword.model import Model as WakeModel
        except Exception as exc:  # pragma: no cover - dependency/runtime issue
            LOGGER.warning("Wake word disabled: %s", exc)
            self._ready = False
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, args=(WakeModel,), daemon=True, name="wake-word-listener"
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _run(self, wake_model_cls) -> None:
        try:
            import sounddevice as sd
            import openwakeword
            from openwakeword.utils import download_models

            wake_word_key = SUPPORTED_WAKE_WORDS.get(self.settings.wake_word_phrase.lower(), "hey_jarvis")

            download_models(model_names=[wake_word_key])
            model_path = openwakeword.MODELS[wake_word_key]["model_path"].replace(".tflite", ".onnx")
            model = wake_model_cls(inference_framework="onnx", wakeword_models=[model_path])
            audio_queue: queue.Queue = queue.Queue()

            def callback(indata, frames, time_info, status) -> None:
                if status:
                    LOGGER.debug("Wake word stream status: %s", status)
                audio_queue.put(indata.copy().reshape(-1))

            resolved_device = resolve_microphone_device(self.settings.microphone_device)
            with sd.InputStream(
                samplerate=16000,
                channels=1,
                dtype="int16",
                callback=callback,
                device=resolved_device,
                blocksize=1280,
            ):
                self._ready = True
                while not self._stop_event.is_set():
                    try:
                        chunk = audio_queue.get(timeout=0.5)
                    except queue.Empty:
                        continue
                    scores = model.predict(chunk)
                    if any(score > 0.5 for score in scores.values()):
                        LOGGER.info("Wake word detected")
                        self.on_detected()
        except Exception as exc:  # pragma: no cover - hardware/runtime issue
            LOGGER.warning("Wake word listener failed: %s", exc)
            self._ready = False
