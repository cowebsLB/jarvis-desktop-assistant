from desktop_voice_assistant.archive import AssistantArchive
from desktop_voice_assistant.models import ResearchSource
from desktop_voice_assistant.research import WebResearcher


class FakeLLM:
    def answer_with_context(self, question: str, context: str) -> str:
        assert question
        assert context
        return "Short researched answer."


class FakeEmbedder:
    def __init__(self, mapping: dict[str, list[float]]) -> None:
        self.mapping = mapping

    def embed(self, text: str):
        for key, value in self.mapping.items():
            if key in text:
                return value
        return None


def test_research_uses_archive_when_no_web_results(tmp_path) -> None:
    archive = AssistantArchive(tmp_path / "assistant.db")
    archive.store_sources(
        "python",
        [ResearchSource(title="Python", url="https://example.com/python", snippet="Language")],
        {"https://example.com/python": "Python is a programming language."},
    )
    researcher = WebResearcher(
        FakeLLM(),
        archive,
        fetch_limit=2,
        embedder=FakeEmbedder({"python": [1.0, 0.0]}),
    )
    archive.store_embedding("https://example.com/python", [1.0, 0.0])
    researcher._search_duckduckgo = lambda query: []

    result = researcher.recall("python")

    assert result is not None
    assert result.from_archive is True
    assert "stored notes" in result.spoken.lower()


def test_research_stores_embeddings_for_fetched_sources(tmp_path) -> None:
    archive = AssistantArchive(tmp_path / "assistant.db")
    researcher = WebResearcher(
        FakeLLM(),
        archive,
        fetch_limit=2,
        embedder=FakeEmbedder({"Pytest docs": [1.0, 0.0]}),
    )
    researcher._search_duckduckgo = lambda query: [
        ResearchSource(title="Pytest docs", url="https://example.com/pytest", snippet="Python tests")
    ]
    researcher._fetch_page_text = lambda url: "Pytest is a testing framework for Python."

    result = researcher.research("python testing")
    hits = archive.semantic_search([1.0, 0.0], limit=1)

    assert result.sources
    assert len(hits) == 1
    assert hits[0].url == "https://example.com/pytest"
