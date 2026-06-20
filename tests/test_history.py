import json
from pathlib import Path

from desktop_voice_assistant.history import HistoryEvent, HistoryRecorder


def test_history_recorder_writes_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "history.jsonl"
    recorder = HistoryRecorder(path)
    recorder.append(
        HistoryEvent(
            kind="request_completed",
            data={"success": True},
            pinned=True,
            summary="Completed request.",
            correlation_id="abc",
        )
    )
    record = json.loads(path.read_text(encoding="utf-8").strip())
    assert record["kind"] == "request_completed"
    assert record["pinned"] is True
    assert record["summary"] == "Completed request."
    assert record["correlation_id"] == "abc"


def test_history_recorder_writes_state_metadata(tmp_path: Path) -> None:
    path = tmp_path / "history.jsonl"
    recorder = HistoryRecorder(path)
    recorder.append(
        HistoryEvent(
            kind="state_transition",
            data={"reason": "test"},
            correlation_id="cid",
            conversation_id="vid",
            state_from="idle",
            state_to="speaking",
        )
    )
    record = json.loads(path.read_text(encoding="utf-8").strip())
    assert record["conversation_id"] == "vid"
    assert record["state_from"] == "idle"
    assert record["state_to"] == "speaking"
