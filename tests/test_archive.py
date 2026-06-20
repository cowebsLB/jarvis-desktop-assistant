from pathlib import Path

from desktop_voice_assistant.archive import AssistantArchive
from desktop_voice_assistant.models import ResearchSource


def test_archive_stores_and_recalls_sources(tmp_path: Path) -> None:
    archive = AssistantArchive(tmp_path / "assistant.db")
    count = archive.store_sources(
        "python testing",
        [ResearchSource(title="Pytest docs", url="https://example.com/pytest", snippet="Testing framework")],
        {"https://example.com/pytest": "Pytest is a Python testing framework."},
    )

    hits = archive.search("python", limit=3)
    assert count == 1
    assert len(hits) == 1
    assert hits[0].title == "Pytest docs"


def test_archive_semantic_search_returns_best_match(tmp_path: Path) -> None:
    archive = AssistantArchive(tmp_path / "assistant.db")
    archive.store_sources(
        "python testing",
        [
            ResearchSource(title="Pytest docs", url="https://example.com/pytest", snippet="Testing framework"),
            ResearchSource(title="Weather docs", url="https://example.com/weather", snippet="Forecasting"),
        ],
        {
            "https://example.com/pytest": "Pytest is a Python testing framework.",
            "https://example.com/weather": "Forecast weather service details.",
        },
    )
    archive.store_embedding("https://example.com/pytest", [1.0, 0.0, 0.0])
    archive.store_embedding("https://example.com/weather", [0.0, 1.0, 0.0])

    hits = archive.semantic_search([0.9, 0.1, 0.0], limit=1)

    assert len(hits) == 1
    assert hits[0].title == "Pytest docs"
