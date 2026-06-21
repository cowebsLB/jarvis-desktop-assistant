from __future__ import annotations

from pathlib import Path

from desktop_voice_assistant.app_memory import AppMemoryStore


class MockLLMAssistant:
    def answer(self, prompt: str) -> str:
        return "mock summary content"


def test_memory_preferences_crud(tmp_path: Path) -> None:
    path = tmp_path / "app_memory.json"
    memory = AppMemoryStore(path)

    # 1. Test Aliases
    memory.remember("chrome browser", "Google Chrome")
    assert memory.resolve("chrome browser") == "Google Chrome"

    # 2. Test Preferences
    memory.set_preference("user_color", "dark_blue")
    assert memory.get_preference("user_color") == "dark_blue"

    # 3. Test Favorite Sites
    memory.set_favorite_site("news", "https://news.ycombinator.com")
    assert memory.get_favorite_site("news") == "https://news.ycombinator.com"

    # 4. Test Preferred Apps
    memory.set_preferred_app("editor", "notepad.exe")
    assert memory.get_preferred_app("editor") == "notepad.exe"


def test_conversational_turn_memory_and_summarization(tmp_path: Path) -> None:
    path = tmp_path / "app_memory.json"
    memory = AppMemoryStore(path)

    # Add less than 5 turns
    memory.add_turn("hi", "hello")
    memory.add_turn("how is weather", "it is sunny")

    context = memory.get_turns_context()
    assert "User: hi" in context
    assert "Jarvis: hello" in context
    assert "User: how is weather" in context
    assert "Jarvis: it is sunny" in context

    # Add up to 5 turns to trigger summarization
    llm = MockLLMAssistant()
    memory.add_turn("turn 3", "reply 3", llm)
    memory.add_turn("turn 4", "reply 4", llm)
    memory.add_turn("turn 5", "reply 5", llm)

    # Verify that turns were summarized and cleared
    context_after = memory.get_turns_context()
    assert "Background of previous turns: mock summary content" in context_after
    assert "User: hi" not in context_after
    assert len(memory._turns) == 0
