from __future__ import annotations

import logging
from pathlib import Path

from .config import APP_DIR
from .history import HISTORY_PATH


def configure_logging() -> Path:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    log_path = APP_DIR / "assistant.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    HISTORY_PATH.touch(exist_ok=True)
    return log_path
