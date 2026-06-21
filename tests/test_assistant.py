from desktop_voice_assistant.actions import ActionExecutor
from desktop_voice_assistant.assistant import DesktopAssistant
from desktop_voice_assistant.archive import AssistantArchive
from desktop_voice_assistant.config import Settings
from desktop_voice_assistant.intent_router import IntentRouter
from desktop_voice_assistant.models import ActionResult, OpenTargetPreview, ResearchResult, ResearchSource, RuntimeState, TranscriptResult
from desktop_voice_assistant.research import WebResearcher
from desktop_voice_assistant.session import SessionSnapshot
import pytest


@pytest.fixture(autouse=True)
def isolate_productivity_db(tmp_path, monkeypatch):
    import desktop_voice_assistant.productivity as prod
    monkeypatch.setattr(prod, "PRODUCTIVITY_PATH", tmp_path / "productivity.json")


class FakeTTS:
    def __init__(self) -> None:
        self.spoken: list[str] = []

    def speak(self, text: str) -> None:
        self.spoken.append(text)


class MissingSTT:
    def transcribe_once(self):
        raise RuntimeError("missing speech model")


class EmptySTT:
    def transcribe_once(self):
        return TranscriptResult(text="", audio_seconds=1.2, ended_early=True)


class UnsupportedSTT:
    def __init__(self, text: str) -> None:
        self.text = text

    def transcribe_once(self):
        return TranscriptResult(text=self.text, audio_seconds=2.0, ended_early=False)


class SequenceSTT:
    def __init__(self, texts: list[str | tuple[str, float]]) -> None:
        self.texts = list(texts)

    def transcribe_once(self):
        item = self.texts.pop(0)
        if isinstance(item, tuple):
            return TranscriptResult(text=item[0], audio_seconds=2.0, ended_early=False, confidence=item[1])
        return TranscriptResult(text=item, audio_seconds=2.0, ended_early=False)


class FakeLLM:
    def answer(self, question: str) -> str:
        return "answer"

    def answer_with_context(self, question: str, context: str) -> str:
        return "answer with context"

    def route_intent(self, transcript: str):
        return None


class FakeWeather:
    def get_summary(self, location: str | None = None):
        class Summary:
            spoken = "Sunny in Beirut."
            details = "Sunny."

        return Summary()


class FakeHistory:
    def __init__(self) -> None:
        self.events = []

    def append(self, event) -> None:
        self.events.append(event)


class FakeHud:
    def __init__(self) -> None:
        self.states: list[tuple[str, str | None]] = []
        self.transcripts: list[str] = []
        self.intents: list[tuple[str, dict[str, str]]] = []
        self.results: list[tuple[str, bool]] = []

    def on_state_change(self, state, reason: str | None = None) -> None:
        self.states.append((state.value if hasattr(state, "value") else str(state), reason))

    def on_transcript(self, transcript: str) -> None:
        self.transcripts.append(transcript)

    def on_intent(self, intent: str, slots: dict[str, str]) -> None:
        self.intents.append((intent, slots))

    def on_result(self, reply: str | None, *, success: bool, sources=None) -> None:
        self.results.append((reply or "", success))


class FakeResearcher:
    def __init__(self) -> None:
        self.research_calls: list[str] = []
        self.recall_calls: list[str] = []

    def research(self, query: str) -> ResearchResult:
        self.research_calls.append(query)
        return ResearchResult(
            query=query,
            answer=f"research answer for {query}",
            spoken=f"spoken answer for {query}",
            sources=[ResearchSource(title="Source One", url="https://example.com/one", snippet="one")],
        )

    def recall(self, query: str, limit: int = 3):
        self.recall_calls.append(query)
        return ResearchResult(
            query=query,
            answer=f"recall answer for {query}",
            spoken=f"recall spoken for {query}",
            sources=[ResearchSource(title="Source One", url="https://example.com/one", snippet="one")],
            from_archive=True,
        )


class MultiSourceResearcher(FakeResearcher):
    def research(self, query: str) -> ResearchResult:
        self.research_calls.append(query)
        return ResearchResult(
            query=query,
            answer=f"research answer for {query}",
            spoken=f"spoken answer for {query}",
            sources=[
                ResearchSource(title="Source One", url="https://example.com/one", snippet="one"),
                ResearchSource(title="Source Two", url="https://example.com/two", snippet="two"),
                ResearchSource(title="Source Three", url="https://example.com/three", snippet="three"),
            ],
        )


class ResearchLLM:
    def answer(self, question: str) -> str:
        return "answer"

    def answer_with_context(self, question: str, context: str) -> str:
        return "Short researched answer."

    def route_intent(self, transcript: str):
        return None


def test_missing_stt_returns_spoken_error() -> None:
    tts = FakeTTS()
    assistant = DesktopAssistant(
        Settings(),
        IntentRouter(),
        ActionExecutor(Settings()),
        MissingSTT(),
        tts,
        FakeLLM(),
        FakeWeather(),
        FakeHistory(),
    )
    result = assistant.listen_and_handle()
    assert not result.success
    assert "speech recognition is not ready" in result.spoken_reply.lower()
    assert tts.spoken


def test_no_speech_returns_helpful_prompt() -> None:
    tts = FakeTTS()
    assistant = DesktopAssistant(
        Settings(),
        IntentRouter(),
        ActionExecutor(Settings()),
        EmptySTT(),
        tts,
        FakeLLM(),
        FakeWeather(),
        FakeHistory(),
    )
    result = assistant.listen_and_handle()
    assert not result.success
    assert "after the beep" in result.spoken_reply.lower()


def test_unsupported_request_returns_specific_feedback() -> None:
    tts = FakeTTS()
    assistant = DesktopAssistant(
        Settings(),
        IntentRouter(),
        ActionExecutor(Settings()),
        UnsupportedSTT("calculate two plus two on the calculator app"),
        tts,
        FakeLLM(),
        FakeWeather(),
        FakeHistory(),
    )
    result = assistant.listen_and_handle()
    assert result.success
    assert "equals 4" in result.spoken_reply.lower()


def test_assistant_records_state_transitions() -> None:
    tts = FakeTTS()
    history = FakeHistory()
    assistant = DesktopAssistant(
        Settings(),
        IntentRouter(),
        ActionExecutor(Settings()),
        EmptySTT(),
        tts,
        FakeLLM(),
        FakeWeather(),
        history,
    )
    assistant.set_runtime_state(RuntimeState.IDLE, reason="test boot")
    assistant.set_runtime_state(RuntimeState.CAPTURING_COMMAND, reason="test capture")
    assistant.listen_and_handle()

    state_events = [event for event in history.events if event.kind == "state_transition"]
    assert state_events
    assert any(event.state_to == RuntimeState.TRANSCRIBING.value for event in state_events)
    assert any(event.state_to == RuntimeState.AWAITING_FOLLOWUP.value for event in state_events)


def test_followup_summarize_that_reuses_last_research_query() -> None:
    tts = FakeTTS()
    history = FakeHistory()
    researcher = FakeResearcher()
    assistant = DesktopAssistant(
        Settings(conversation_followup_seconds=45),
        IntentRouter(),
        ActionExecutor(Settings()),
        SequenceSTT(["search the web for python testing", "summarize that"]),
        tts,
        FakeLLM(),
        FakeWeather(),
        history,
        researcher,
    )

    first = assistant.listen_and_handle()
    second = assistant.listen_and_handle()

    assert first.success
    assert second.success
    assert researcher.research_calls == ["python testing"]
    assert researcher.recall_calls[-1] == "python testing"


def test_followup_open_it_opens_last_source(monkeypatch) -> None:
    tts = FakeTTS()
    history = FakeHistory()
    researcher = FakeResearcher()
    opened: list[str] = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url))
    assistant = DesktopAssistant(
        Settings(conversation_followup_seconds=45),
        IntentRouter(),
        ActionExecutor(Settings()),
        SequenceSTT(["search the web for python testing", "open it"]),
        tts,
        FakeLLM(),
        FakeWeather(),
        history,
        researcher,
    )

    assistant.listen_and_handle()
    second = assistant.listen_and_handle()

    assert second.success
    assert opened == ["https://example.com/one"]


def test_followup_open_second_one_opens_second_source(monkeypatch) -> None:
    tts = FakeTTS()
    history = FakeHistory()
    researcher = MultiSourceResearcher()
    opened: list[str] = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url))
    assistant = DesktopAssistant(
        Settings(conversation_followup_seconds=45),
        IntentRouter(),
        ActionExecutor(Settings()),
        SequenceSTT(["search the web for python testing", "open the second one"]),
        tts,
        FakeLLM(),
        FakeWeather(),
        history,
        researcher,
    )

    assistant.listen_and_handle()
    second = assistant.listen_and_handle()

    assert second.success
    assert opened == ["https://example.com/two"]


def test_followup_summarize_second_one_recalls_second_source_title() -> None:
    tts = FakeTTS()
    history = FakeHistory()
    researcher = MultiSourceResearcher()
    assistant = DesktopAssistant(
        Settings(conversation_followup_seconds=45),
        IntentRouter(),
        ActionExecutor(Settings()),
        SequenceSTT(["search the web for python testing", "summarize the second one"]),
        tts,
        FakeLLM(),
        FakeWeather(),
        history,
        researcher,
    )

    assistant.listen_and_handle()
    second = assistant.listen_and_handle()

    assert second.success
    assert researcher.recall_calls[-1] == "Source Two"


def test_followup_expires_and_does_not_reuse_previous_context() -> None:
    tts = FakeTTS()
    history = FakeHistory()
    researcher = FakeResearcher()
    assistant = DesktopAssistant(
        Settings(conversation_followup_seconds=45),
        IntentRouter(),
        ActionExecutor(Settings()),
        SequenceSTT(["search the web for python testing", "summarize that"]),
        tts,
        FakeLLM(),
        FakeWeather(),
        history,
        researcher,
    )

    first = assistant.listen_and_handle()
    assistant.session.snapshot = SessionSnapshot(conversation_id="expired", followup_until=None)
    second = assistant.listen_and_handle()

    assert first.success
    assert second.success
    assert researcher.recall_calls == ["that"]


def test_web_search_handles_fetch_failures_without_state_transition_crash(tmp_path) -> None:
    tts = FakeTTS()
    history = FakeHistory()
    archive = AssistantArchive(tmp_path / "assistant.db")
    researcher = WebResearcher(ResearchLLM(), archive, fetch_limit=2, archive_enabled=False)
    researcher._search_duckduckgo = lambda query: [
        ResearchSource(title="Source One", url="https://example.com/one", snippet="one"),
    ]
    researcher._fetch_page_text = lambda url: ""
    assistant = DesktopAssistant(
        Settings(),
        IntentRouter(),
        ActionExecutor(Settings()),
        SequenceSTT([]),
        tts,
        FakeLLM(),
        FakeWeather(),
        history,
        researcher,
    )

    result = assistant.handle_text_input("search the web for python testing")

    assert result.success
    assert "loaded poorly" in result.message.lower()
    assert assistant.runtime_state == RuntimeState.AWAITING_FOLLOWUP


def test_contextless_open_it_requests_clarification() -> None:
    tts = FakeTTS()
    history = FakeHistory()
    assistant = DesktopAssistant(
        Settings(conversation_followup_seconds=45),
        IntentRouter(),
        ActionExecutor(Settings()),
        SequenceSTT(["open it"]),
        tts,
        FakeLLM(),
        FakeWeather(),
        history,
    )

    result = assistant.listen_and_handle()

    assert not result.success
    assert "what would you like me to open" in result.spoken_reply.lower()
    assert assistant.session.snapshot.pending_clarification is not None


def test_fuzzy_app_match_requires_confirmation(monkeypatch) -> None:
    tts = FakeTTS()
    history = FakeHistory()
    action = ActionExecutor(Settings())
    monkeypatch.setattr(
        action,
        "preview_open_target",
        lambda target: OpenTargetPreview(
            requested_target="spotfy",
            resolved_target="spotfy",
            fuzzy_match="spotify",
            launchable=True,
        ),
    )
    assistant = DesktopAssistant(
        Settings(conversation_followup_seconds=45),
        IntentRouter(),
        action,
        SequenceSTT(["open spotfy"]),
        tts,
        FakeLLM(),
        FakeWeather(),
        history,
    )

    result = assistant.listen_and_handle()

    assert not result.success
    assert "do you want spotify" in result.spoken_reply.lower()
    assert assistant.session.snapshot.pending_confirmation is not None


def test_confirmation_yes_executes_pending_open(monkeypatch) -> None:
    tts = FakeTTS()
    history = FakeHistory()
    action = ActionExecutor(Settings())
    monkeypatch.setattr(
        action,
        "preview_open_target",
        lambda target: OpenTargetPreview(
            requested_target="spotfy",
            resolved_target="spotfy",
            fuzzy_match="spotify",
            launchable=True,
        ),
    )
    monkeypatch.setattr(
        action,
        "execute",
        lambda intent: ActionResult(
            True,
            f"Opened app: {intent.slots['target']}",
            f"Opening {intent.slots['target']}.",
            opened_target=intent.slots["target"],
        ),
    )
    assistant = DesktopAssistant(
        Settings(conversation_followup_seconds=45),
        IntentRouter(),
        action,
        SequenceSTT(["open spotfy", "yes"]),
        tts,
        FakeLLM(),
        FakeWeather(),
        history,
    )

    first = assistant.listen_and_handle()
    second = assistant.listen_and_handle()

    assert not first.success
    assert second.success
    assert "spotify" in second.message.lower()
    assert assistant.session.snapshot.pending_confirmation is None


def test_confirmation_no_cancels_pending_open(monkeypatch) -> None:
    tts = FakeTTS()
    history = FakeHistory()
    action = ActionExecutor(Settings())
    monkeypatch.setattr(
        action,
        "preview_open_target",
        lambda target: OpenTargetPreview(
            requested_target="spotfy",
            resolved_target="spotfy",
            fuzzy_match="spotify",
            launchable=True,
        ),
    )
    assistant = DesktopAssistant(
        Settings(conversation_followup_seconds=45),
        IntentRouter(),
        action,
        SequenceSTT(["open spotfy", "no"]),
        tts,
        FakeLLM(),
        FakeWeather(),
        history,
    )

    first = assistant.listen_and_handle()
    second = assistant.listen_and_handle()

    assert not first.success
    assert second.success
    assert "cancelled" in second.message.lower()
    assert assistant.session.snapshot.pending_confirmation is None


def test_assistant_emits_hud_events() -> None:
    tts = FakeTTS()
    history = FakeHistory()
    hud = FakeHud()
    assistant = DesktopAssistant(
        Settings(),
        IntentRouter(),
        ActionExecutor(Settings()),
        SequenceSTT(["what's the weather in beirut"]),
        tts,
        FakeLLM(),
        FakeWeather(),
        history,
        hud=hud,
    )

    result = assistant.listen_and_handle()

    assert result.success
    assert hud.transcripts == ["what's the weather in beirut"]
    assert hud.intents and hud.intents[0][0] == "weather"
    assert hud.results and hud.results[-1][1] is True
    assert any(state == RuntimeState.TRANSCRIBING.value for state, _ in hud.states)
    assert any(state == RuntimeState.SPEAKING.value for state, _ in hud.states)


def test_assistant_handles_hud_text_input() -> None:
    tts = FakeTTS()
    history = FakeHistory()
    hud = FakeHud()
    assistant = DesktopAssistant(
        Settings(),
        IntentRouter(),
        ActionExecutor(Settings()),
        SequenceSTT([]),
        tts,
        FakeLLM(),
        FakeWeather(),
        history,
        hud=hud,
    )

    result = assistant.handle_text_input("what's the weather in beirut")

    assert result.success
    assert hud.transcripts == ["what's the weather in beirut"]
    assert hud.intents and hud.intents[0][0] == "weather"


def test_real_hud_queues_events() -> None:
    from desktop_voice_assistant.hud import FloatingHud
    from desktop_voice_assistant.models import RuntimeState
    settings = Settings()
    hud = FloatingHud(settings)
    hud.on_state_change(RuntimeState.PLANNING, "test plan")
    hud.on_transcript("hello world")
    hud.on_intent("weather", {"location": "beirut"})
    hud.on_result("fine weather", success=True, sources=[])
    hud.on_history_event({"kind": "test", "summary": "tested HUD"})
    hud.wake_detected()
    
    assert hud.queue.qsize() == 6


def test_real_hud_toggle_updates_enabled_state() -> None:
    from desktop_voice_assistant.hud import FloatingHud

    settings = Settings(hud_enabled=True)
    hud = FloatingHud(settings)

    hud.set_enabled(False)
    assert settings.hud_enabled is False
    assert hud._enabled is False

    hud.set_enabled(True)
    assert settings.hud_enabled is True
    assert hud._enabled is True


def test_assistant_productivity_routing() -> None:
    from desktop_voice_assistant.assistant import DesktopAssistant
    from desktop_voice_assistant.intent_router import IntentRouter
    from desktop_voice_assistant.actions import ActionExecutor
    from desktop_voice_assistant.config import Settings
    from pathlib import Path
    
    tts = FakeTTS()
    history = FakeHistory()
    assistant = DesktopAssistant(
        Settings(),
        IntentRouter(),
        ActionExecutor(Settings()),
        SequenceSTT([]),
        tts,
        FakeLLM(),
        FakeWeather(),
        history,
    )
    
    assistant.productivity.clear_tasks()
    
    result = assistant.handle_text_input("add buy bread to my task list")
    assert result.success
    assert "Added" in result.message
    
    result_list = assistant.handle_text_input("list my tasks")
    assert result_list.success
    assert "buy bread" in result_list.message
    
    result_timer = assistant.handle_text_input("set a timer for 10 minutes")
    assert result_timer.success
    assert "Timer set" in result_timer.message

    result_note = assistant.handle_text_input("take a note that meeting is at two")
    assert result_note.success
    assert "Note saved" in result_note.message

    notes_file = Path.home() / ".desktop_voice_assistant" / "quick-notes.md"
    assert notes_file.exists()
    assert "meeting is at two" in notes_file.read_text(encoding="utf-8")
    
    assistant.productivity.stop()


def test_assistant_browser_summarize(monkeypatch) -> None:
    from desktop_voice_assistant.assistant import DesktopAssistant
    from desktop_voice_assistant.intent_router import IntentRouter
    from desktop_voice_assistant.actions import ActionExecutor
    from desktop_voice_assistant.config import Settings
    
    tts = FakeTTS()
    history = FakeHistory()
    assistant = DesktopAssistant(
        Settings(),
        IntentRouter(),
        ActionExecutor(Settings()),
        SequenceSTT([]),
        tts,
        FakeLLM(),
        FakeWeather(),
        history,
    )
    
    monkeypatch.setattr(assistant.actions, "_get_active_page_text", lambda: "active web page content details")
    
    result = assistant.handle_text_input("summarize this page")
    assert result.success
    assert "mock" in result.message.lower() or "answer" in result.message.lower()
    
    assistant.productivity.stop()


def test_llm_intent_routing_fallback() -> None:
    class RoutingFakeLLM:
        def __init__(self) -> None:
            self.routed_queries = []

        def answer(self, question: str) -> str:
            return "answer"

        def answer_with_context(self, question: str, context: str) -> str:
            return "answer with context"

        def route_intent(self, transcript: str):
            self.routed_queries.append(transcript)
            from desktop_voice_assistant.models import IntentResult
            if "countdown" in transcript:
                return IntentResult("set_timer", 0.95, {"duration": "10", "unit": "minutes"})
            return None

    tts = FakeTTS()
    history = FakeHistory()
    llm = RoutingFakeLLM()
    assistant = DesktopAssistant(
        Settings(),
        IntentRouter(),
        ActionExecutor(Settings()),
        UnsupportedSTT("make a countdown for ten minutes"),
        tts,
        llm,
        FakeWeather(),
        history,
    )
    result = assistant.listen_and_handle()
    assert result.success
    assert "timer set" in result.spoken_reply.lower()
    assert llm.routed_queries == ["make a countdown for ten minutes"]
    assistant.productivity.stop()


def test_destructive_request_requires_confirmation() -> None:
    tts = FakeTTS()
    history = FakeHistory()
    action = ActionExecutor(Settings())
    assistant = DesktopAssistant(
        Settings(conversation_followup_seconds=45),
        IntentRouter(),
        action,
        SequenceSTT(["clear my task list", "yes"]),
        tts,
        FakeLLM(),
        FakeWeather(),
        history,
    )

    first = assistant.listen_and_handle()
    assistant.productivity.clear_tasks()
    assert not first.success
    assert "are you sure you want to clear tasks" in first.spoken_reply.lower()
    assert assistant.session.snapshot.pending_confirmation is not None

    assistant.productivity.add_task("test task")
    assert len(assistant.productivity.list_tasks()) == 1

    second = assistant.listen_and_handle()
    assert second.success
    assert "task list cleared" in second.message.lower()
    assert len(assistant.productivity.list_tasks()) == 0
    assert assistant.session.snapshot.pending_confirmation is None
    assistant.productivity.stop()


def test_confirmation_policy_always_requires_confirmation_for_open_target(monkeypatch) -> None:
    tts = FakeTTS()
    history = FakeHistory()
    action = ActionExecutor(Settings())
    monkeypatch.setattr(
        action,
        "preview_open_target",
        lambda target: OpenTargetPreview(
            requested_target="notepad",
            resolved_target="notepad",
            exact_match=True,
            launchable=True,
        ),
    )
    assistant = DesktopAssistant(
        Settings(confirmation_policy="always"),
        IntentRouter(),
        action,
        SequenceSTT(["open notepad"]),
        tts,
        FakeLLM(),
        FakeWeather(),
        history,
    )

    result = assistant.listen_and_handle()

    assert not result.success
    assert "confirm opening notepad" in result.spoken_reply.lower()
    assert assistant.session.snapshot.pending_confirmation is not None


def test_low_confidence_stt_clarification_loop() -> None:
    tts = FakeTTS()
    history = FakeHistory()
    stt = SequenceSTT([
        ("gibberish", 0.3),
        ("what's the weather in Beirut", 0.95),
    ])
    assistant = DesktopAssistant(
        Settings(),
        IntentRouter(),
        ActionExecutor(Settings()),
        stt,
        tts,
        FakeLLM(),
        FakeWeather(),
        history,
    )

    first = assistant.listen_and_handle()
    assert not first.success
    assert "didn't quite catch that" in first.spoken_reply.lower()
    assert assistant.session.snapshot.pending_clarification is not None
    assert assistant.session.snapshot.pending_clarification.intent_name == "low_confidence"
    assert assistant.runtime_state == RuntimeState.CLARIFYING

    second = assistant.listen_and_handle()
    assert second.success
    assert "sunny" in second.message.lower()
    assert assistant.session.snapshot.pending_clarification is None
    assert assistant.runtime_state == RuntimeState.AWAITING_FOLLOWUP
    assistant.productivity.stop()


def test_power_action_requires_confirmation() -> None:
    tts = FakeTTS()
    history = FakeHistory()
    action = ActionExecutor(Settings())
    assistant = DesktopAssistant(
        Settings(conversation_followup_seconds=45),
        IntentRouter(),
        action,
        SequenceSTT(["shutdown the system", "yes"]),
        tts,
        FakeLLM(),
        FakeWeather(),
        history,
    )

    first = assistant.listen_and_handle()
    assert not first.success
    assert "are you sure you want to power action" in first.spoken_reply.lower()
    assert assistant.session.snapshot.pending_confirmation is not None

    second = assistant.listen_and_handle()
    assert second.success
    assert "simulated system shutdown completed" in second.message.lower()
    assert assistant.session.snapshot.pending_confirmation is None
    assistant.productivity.stop()


def test_delete_file_requires_confirmation(tmp_path) -> None:
    test_file = tmp_path / "test_delete.txt"
    test_file.write_text("hello delete")
    assert test_file.exists()

    tts = FakeTTS()
    history = FakeHistory()
    action = ActionExecutor(Settings())
    assistant = DesktopAssistant(
        Settings(conversation_followup_seconds=45),
        IntentRouter(),
        action,
        SequenceSTT([f"delete file {test_file}", "yes"]),
        tts,
        FakeLLM(),
        FakeWeather(),
        history,
    )

    first = assistant.listen_and_handle()
    assert not first.success
    assert "are you sure you want to delete file" in first.spoken_reply.lower()
    assert assistant.session.snapshot.pending_confirmation is not None

    second = assistant.listen_and_handle()
    assert second.success
    assert "deleted file" in second.message.lower()
    assert not test_file.exists()
    assert assistant.session.snapshot.pending_confirmation is None
    assistant.productivity.stop()


def test_send_email_requires_confirmation(monkeypatch) -> None:
    opened_urls = []
    import webbrowser
    monkeypatch.setattr(webbrowser, "open", lambda url: opened_urls.append(url))

    tts = FakeTTS()
    history = FakeHistory()
    action = ActionExecutor(Settings())
    assistant = DesktopAssistant(
        Settings(conversation_followup_seconds=45),
        IntentRouter(),
        action,
        SequenceSTT(["send email to john@example.com", "yes"]),
        tts,
        FakeLLM(),
        FakeWeather(),
        history,
    )

    first = assistant.listen_and_handle()
    assert not first.success
    assert "are you sure you want to send email" in first.spoken_reply.lower()
    assert assistant.session.snapshot.pending_confirmation is not None

    second = assistant.listen_and_handle()
    assert second.success
    assert "drafted email to john@example.com" in second.message.lower()
    assert len(opened_urls) == 1
    assert "mailto:john@example.com" in opened_urls[0]
    assert assistant.session.snapshot.pending_confirmation is None
    assistant.productivity.stop()

