from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from desktop_voice_assistant.productivity import (
    ProductivityManager,
    calculate_alarm_time,
    parse_duration_to_seconds,
)


def test_parse_duration_to_seconds() -> None:
    assert parse_duration_to_seconds("10", "second") == 10
    assert parse_duration_to_seconds("5", "min") == 300
    assert parse_duration_to_seconds("2", "hour") == 7200


def test_calculate_alarm_time() -> None:
    # Set alarm for 8 AM
    alarm_time = calculate_alarm_time(8, 0, "am")
    now = datetime.now(UTC)
    # Trigger time must be in the future
    assert alarm_time > now
    # Trigger time difference must be less than 25 hours
    assert alarm_time - now < timedelta(hours=25)


def test_productivity_manager_crud(tmp_path: Path) -> None:
    path = tmp_path / "productivity.json"
    
    triggered_alerts = []
    def on_alert(msg: str) -> None:
        triggered_alerts.append(msg)

    mgr = ProductivityManager(path, on_notification=on_alert)

    # 1. Test Tasks
    mgr.add_task("Buy bread")
    mgr.add_task("Call dentist")
    assert mgr.list_tasks() == ["Buy bread", "Call dentist"]
    
    mgr.clear_tasks()
    assert mgr.list_tasks() == []

    # 2. Test Timers/Reminders trigger
    mgr.add_timer("cook pasta", 0)  # trigger immediately
    mgr.add_reminder("call doctor", 0)  # trigger immediately
    
    # Run alert check
    mgr.check_alerts()
    
    assert len(triggered_alerts) == 2
    assert any("pasta" in alert for alert in triggered_alerts)
    assert any("doctor" in alert for alert in triggered_alerts)
    
    # Verify they were removed
    assert len(mgr.timers) == 0
    assert len(mgr.reminders) == 0
