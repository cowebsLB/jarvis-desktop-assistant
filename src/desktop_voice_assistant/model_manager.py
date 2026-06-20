from __future__ import annotations

import logging

from .config import Settings


LOGGER = logging.getLogger(__name__)


class ModelManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def is_installed(self) -> bool:
        try:
            import faster_whisper  # noqa: F401
        except Exception:
            return False
        return True

    def install_stt_model(self) -> str:
        from faster_whisper import WhisperModel

        LOGGER.info(
            "Warming faster-whisper model name=%s device=%s compute_type=%s",
            self.settings.stt_model_name,
            self.settings.stt_device,
            self.settings.stt_compute_type,
        )
        WhisperModel(
            self.settings.stt_model_name,
            device=self.settings.stt_device,
            compute_type=self.settings.stt_compute_type,
        )
        return self.settings.stt_model_name
