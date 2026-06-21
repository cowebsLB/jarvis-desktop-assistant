from __future__ import annotations

import json
import logging
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from .config import APP_DIR

LOGGER = logging.getLogger(__name__)
PRODUCTIVITY_PATH = APP_DIR / "productivity.json"


def parse_duration_to_seconds(duration_str: str, unit_str: str) -> int:
    val = int(duration_str)
    unit = unit_str.lower()
    if unit in ["second", "sec"]:
        return val
    elif unit in ["minute", "min"]:
        return val * 60
    elif unit in ["hour", "hr"]:
        return val * 3600
    return val


def calculate_alarm_time(hour: int, minute: int, period: str) -> datetime:
    now = datetime.now()
    hr = hour
    p = period.lower()
    if p == "pm" and hr < 12:
        hr += 12
    elif p == "am" and hr == 12:
        hr = 0
    elif p == "" and hr < 12:
        # If no period, assume PM if hour is reasonable (e.g. set alarm for 7, now is 2pm -> assume 7pm or next occurrence)
        target_today = now.replace(hour=hr, minute=minute, second=0, microsecond=0)
        if target_today <= now:
            # check if 12-hour offset is better
            target_pm = now.replace(hour=hr + 12, minute=minute, second=0, microsecond=0)
            if target_pm > now:
                target_today = target_pm
        target = target_today
    
    target = now.replace(hour=hr, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return target.astimezone(UTC)


class ProductivityManager:
    def __init__(self, path: Path = PRODUCTIVITY_PATH, on_notification: Callable[[str], None] | None = None) -> None:
        self.path = path
        self.on_notification = on_notification
        self.lock = threading.Lock()
        self.active = False
        self.thread: threading.Thread | None = None

        self.tasks: list[dict[str, Any]] = []
        self.reminders: list[dict[str, Any]] = []
        self.timers: list[dict[str, Any]] = []
        self.alarms: list[dict[str, Any]] = []

        self.load()

    def start(self) -> None:
        with self.lock:
            if self.active:
                return
            self.active = True
            self.thread = threading.Thread(target=self._scheduler_loop, daemon=True, name="productivity-scheduler")
            self.thread.start()
            LOGGER.info("Productivity scheduler started.")

    def stop(self) -> None:
        with self.lock:
            self.active = False
        if self.thread:
            self.thread.join(timeout=1.0)
            LOGGER.info("Productivity scheduler stopped.")

    def load(self) -> None:
        with self.lock:
            if not self.path.exists():
                self._save_state()
                return
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                self.tasks = data.get("tasks", [])
                self.reminders = data.get("reminders", [])
                self.timers = data.get("timers", [])
                self.alarms = data.get("alarms", [])
            except Exception as exc:
                LOGGER.exception("Failed to load productivity data: %s", exc)

    def save(self) -> None:
        with self.lock:
            self._save_state()

    def _save_state(self) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "tasks": self.tasks,
            "reminders": self.reminders,
            "timers": self.timers,
            "alarms": self.alarms,
        }
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # --- Reminders API ---

    def add_reminder(self, text: str, duration_sec: int) -> dict[str, Any]:
        trigger_time = datetime.now(UTC) + timedelta(seconds=duration_sec)
        reminder = {
            "id": str(uuid4()),
            "text": text,
            "trigger_time": trigger_time.isoformat(),
            "created_at": datetime.now(UTC).isoformat(),
        }
        with self.lock:
            self.reminders.append(reminder)
            self._save_state()
        return reminder

    # --- Timers API ---

    def add_timer(self, label: str, duration_sec: int) -> dict[str, Any]:
        trigger_time = datetime.now(UTC) + timedelta(seconds=duration_sec)
        timer = {
            "id": str(uuid4()),
            "label": label,
            "duration_seconds": duration_sec,
            "trigger_time": trigger_time.isoformat(),
            "created_at": datetime.now(UTC).isoformat(),
        }
        with self.lock:
            self.timers.append(timer)
            self._save_state()
        return timer

    # --- Alarms API ---

    def add_alarm(self, hour: int, minute: int, period: str) -> dict[str, Any]:
        trigger_time = calculate_alarm_time(hour, minute, period)
        alarm = {
            "id": str(uuid4()),
            "hour": hour,
            "minute": minute,
            "period": period,
            "trigger_time": trigger_time.isoformat(),
            "created_at": datetime.now(UTC).isoformat(),
        }
        with self.lock:
            self.alarms.append(alarm)
            self._save_state()
        return alarm

    # --- Tasks API ---

    def add_task(self, content: str) -> dict[str, Any]:
        task = {
            "id": str(uuid4()),
            "content": content,
            "created_at": datetime.now(UTC).isoformat(),
        }
        with self.lock:
            self.tasks.append(task)
            self._save_state()
        return task

    def list_tasks(self) -> list[str]:
        with self.lock:
            return [t["content"] for t in self.tasks]

    def clear_tasks(self) -> None:
        with self.lock:
            self.tasks.clear()
            self._save_state()

    # --- Scheduler Thread Loop ---

    def _scheduler_loop(self) -> None:
        while True:
            with self.lock:
                if not self.active:
                    break
            self.check_alerts()
            time.sleep(1.0)

    def check_alerts(self) -> None:
        now = datetime.now(UTC)
        triggered_msgs = []

        with self.lock:
            # Check reminders
            active_reminders = []
            for rem in self.reminders:
                try:
                    trig = datetime.fromisoformat(rem["trigger_time"])
                    if now >= trig:
                        triggered_msgs.append(f"Reminder: {rem['text']}")
                    else:
                        active_reminders.append(rem)
                except Exception:
                    pass
            self.reminders = active_reminders

            # Check timers
            active_timers = []
            for tmr in self.timers:
                try:
                    trig = datetime.fromisoformat(tmr["trigger_time"])
                    if now >= trig:
                        triggered_msgs.append(f"Timer alert: {tmr['label']} is done!")
                    else:
                        active_timers.append(tmr)
                except Exception:
                    pass
            self.timers = active_timers

            # Check alarms
            active_alarms = []
            for alm in self.alarms:
                try:
                    trig = datetime.fromisoformat(alm["trigger_time"])
                    if now >= trig:
                        triggered_msgs.append(f"Alarm trigger alert!")
                    else:
                        active_alarms.append(alm)
                except Exception:
                    pass
            self.alarms = active_alarms

            if triggered_msgs:
                self._save_state()

        # Dispatch notifications
        for msg in triggered_msgs:
            if self.on_notification:
                try:
                    self.on_notification(msg)
                except Exception as exc:
                    LOGGER.error("Failed to trigger alert callback: %s", exc)
