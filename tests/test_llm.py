from desktop_voice_assistant.llm import HybridAssistant


class FakeBackend:
    def __init__(self, label: str) -> None:
        self.label = label
        self.model = f"{label}-model"
        self.assistant_name = "Jarvis"
        self.assistant_style = "stark-butler"
        self.calls: list[tuple[str, str]] = []
        self.fail = False

    def update_settings(self, *, model=None, assistant_name=None, assistant_style=None) -> None:
        if model:
            self.model = model
        if assistant_name:
            self.assistant_name = assistant_name
        if assistant_style:
            self.assistant_style = assistant_style

    def system_prompt(self) -> str:
        return f"{self.label}-prompt"

    def answer(self, question: str) -> str:
        self.calls.append(("answer", question))
        if self.fail:
            raise RuntimeError(f"{self.label} failed")
        return f"{self.label}:{question}"

    def answer_with_context(self, question: str, context: str) -> str:
        self.calls.append(("answer_with_context", question))
        if self.fail:
            raise RuntimeError(f"{self.label} failed")
        return f"{self.label}:{question}:{len(context)}"

    def route_intent(self, transcript: str):
        self.calls.append(("route_intent", transcript))
        return None


def test_hybrid_uses_local_for_simple_question() -> None:
    local = FakeBackend("local")
    remote = FakeBackend("gemini")
    llm = HybridAssistant(local, remote)

    result = llm.answer("What time is it in Beirut?")

    assert result.startswith("local:")
    assert local.calls == [("answer", "What time is it in Beirut?")]
    assert remote.calls == []


def test_hybrid_uses_gemini_for_complex_question() -> None:
    local = FakeBackend("local")
    remote = FakeBackend("gemini")
    llm = HybridAssistant(local, remote)

    result = llm.answer("Compare the tradeoffs of three desktop automation architectures and explain the best plan in detail.")

    assert result.startswith("gemini:")
    assert remote.calls == [("answer", "Compare the tradeoffs of three desktop automation architectures and explain the best plan in detail.")]


def test_hybrid_falls_back_to_local_when_gemini_fails() -> None:
    local = FakeBackend("local")
    remote = FakeBackend("gemini")
    remote.fail = True
    llm = HybridAssistant(local, remote)

    result = llm.answer("Analyze the architecture tradeoffs in detail.")

    assert result.startswith("local:")
    assert remote.calls == [("answer", "Analyze the architecture tradeoffs in detail.")]
    assert local.calls == [("answer", "Analyze the architecture tradeoffs in detail.")]


def test_hybrid_uses_gemini_for_large_context() -> None:
    local = FakeBackend("local")
    remote = FakeBackend("gemini")
    llm = HybridAssistant(local, remote)

    result = llm.answer_with_context("Summarize this page.", "x" * 2000)

    assert result.startswith("gemini:")
    assert remote.calls == [("answer_with_context", "Summarize this page.")]
