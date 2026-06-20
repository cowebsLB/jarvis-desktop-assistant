from desktop_voice_assistant.actions import ActionExecutor
from desktop_voice_assistant.assistant import DesktopAssistant
from desktop_voice_assistant.config import Settings
from desktop_voice_assistant.intent_router import IntentRouter
from desktop_voice_assistant.models import ActionResult, OpenTargetPreview, ResearchResult, ResearchSource, RuntimeState, TranscriptResult
from desktop_voice_assistant.session import SessionSnapshot


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
    def __init__(self, texts: list[str]) -> None:
        self.texts = list(texts)

    def transcribe_once(self):
        text = self.texts.pop(0)
        return TranscriptResult(text=text, audio_seconds=2.0, ended_early=False)


class FakeLLM:
    def answer(self, question: str) -> str:
        return "answer"

    def answer_with_context(self, question: str, context: str) -> str:
        return "answer with context"


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
