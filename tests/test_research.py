from desktop_voice_assistant.archive import AssistantArchive
from desktop_voice_assistant.models import ResearchSource
from desktop_voice_assistant.research import WebResearcher


class FakeLLM:
    def answer_with_context(self, question: str, context: str) -> str:
        assert question
        assert context
        return "Short researched answer."


class FakeEmbedder:
    def __init__(self, mapping: dict[str, list[float]], *, last_error: str | None = None, warmed_successfully: bool = True) -> None:
        self.mapping = mapping
        self.last_error = last_error
        self.warmed_successfully = warmed_successfully

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


def test_recall_marks_stale_archive_notes_cautiously(tmp_path) -> None:
    archive = AssistantArchive(tmp_path / "assistant.db")
    archive.store_sources(
        "python",
        [ResearchSource(title="Python", url="https://example.com/python", snippet="Language")],
        {"https://example.com/python": "Python is a programming language."},
    )
    with archive._connect() as connection:
        connection.execute(
            "UPDATE web_pages SET fetched_at = ? WHERE url = ?",
            ("2020-01-01T00:00:00+00:00", "https://example.com/python"),
        )

    researcher = WebResearcher(FakeLLM(), archive, embedder=FakeEmbedder({"python": [1.0, 0.0]}))
    archive.store_embedding("https://example.com/python", [1.0, 0.0])

    result = researcher.recall("python")

    assert result is not None
    assert "stale" in result.answer.lower()


def test_research_adds_cautious_note_when_live_sources_conflict(tmp_path) -> None:
    archive = AssistantArchive(tmp_path / "assistant.db")
    researcher = WebResearcher(FakeLLM(), archive, fetch_limit=2, embedder=FakeEmbedder({}))
    researcher._search_duckduckgo = lambda query: [
        ResearchSource(title="Source One", url="https://example.com/one", snippet="Population 10"),
        ResearchSource(title="Source Two", url="https://example.com/two", snippet="Population 20"),
    ]
    researcher._fetch_page_text = lambda url: "Population 10" if url.endswith("/one") else "Population 20"

    result = researcher.research("population")

    assert "conflict" in result.answer.lower() or "cautious" in result.answer.lower()


def test_recall_reports_keyword_fallback_when_embeddings_degrade(tmp_path) -> None:
    archive = AssistantArchive(tmp_path / "assistant.db")
    archive.store_sources(
        "python",
        [ResearchSource(title="Python", url="https://example.com/python", snippet="Language")],
        {"https://example.com/python": "Python is a programming language."},
    )
    researcher = WebResearcher(
        FakeLLM(),
        archive,
        embedder=FakeEmbedder({}, last_error="model missing", warmed_successfully=False),
    )

    result = researcher.recall("python")

    assert result is not None
    assert "keyword-only mode" in result.spoken.lower()


def test_research_result_keeps_sources_when_available(tmp_path) -> None:
    archive = AssistantArchive(tmp_path / "assistant.db")
    researcher = WebResearcher(FakeLLM(), archive, fetch_limit=2, embedder=FakeEmbedder({}))
    researcher._search_duckduckgo = lambda query: [
        ResearchSource(title="Pytest docs", url="https://example.com/pytest", snippet="Python tests")
    ]
    researcher._fetch_page_text = lambda url: "Pytest is a testing framework for Python."

    result = researcher.research("python testing")

    assert len(result.sources) == 1
    assert result.sources[0].url == "https://example.com/pytest"
