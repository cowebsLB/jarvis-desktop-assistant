from __future__ import annotations

import html
import logging
import re
from urllib.parse import quote_plus

import requests

from .archive import AssistantArchive
from .models import RuntimeState
from .embeddings import EmbeddingService
from .models import ResearchResult, ResearchSource


LOGGER = logging.getLogger(__name__)


class WebResearcher:
    def __init__(
        self,
        llm,
        archive: AssistantArchive,
        fetch_limit: int = 3,
        embedder: EmbeddingService | None = None,
        archive_enabled: bool = True,
        on_state_change=None,
    ) -> None:
        self.llm = llm
        self.archive = archive
        self.fetch_limit = fetch_limit
        self.embedder = embedder
        self.archive_enabled = archive_enabled
        self.on_state_change = on_state_change
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                )
            }
        )

    def research(self, query: str) -> ResearchResult:
        LOGGER.info("Researching web query: %s", query)
        embedding_note = self._embedding_status_note()
        self._emit_state(RuntimeState.RESEARCHING, "starting web research")
        pages = self._search_duckduckgo(query)
        if not pages:
            archive_result = self.recall(query)
            if archive_result:
                return archive_result
            return ResearchResult(
                query=query,
                answer="No useful web results were found.",
                spoken=self._append_status_notes("I couldn't find useful web results.", embedding_note),
            )

        page_content: dict[str, str] = {}
        context_blocks: list[str] = []
        usable_sources: list[ResearchSource] = []
        self._emit_state(RuntimeState.FETCHING_SOURCES, "fetching source pages")
        for source in pages[: self.fetch_limit]:
            content = self._fetch_page_text(source.url)
            if not content:
                continue
            page_content[source.url] = content
            usable_sources.append(
                ResearchSource(
                    title=source.title,
                    url=source.url,
                    snippet=source.snippet,
                )
            )
            context_blocks.append(
                f"Title: {source.title}\nURL: {source.url}\nSnippet: {source.snippet}\nContent: {content[:1800]}"
            )

        if not usable_sources:
            archive_result = self.recall(query)
            if archive_result:
                return archive_result
            return ResearchResult(
                query=query,
                answer="The pages loaded poorly, so I don't have a reliable answer yet.",
                spoken=self._append_status_notes("The pages loaded poorly, so I don't have a reliable answer yet.", embedding_note),
            )

        self._emit_state(RuntimeState.RANKING_SOURCES, "ranking source pages")
        evidence_note = self._build_evidence_note(query, usable_sources, page_content)
        prompt = (
            f"Question: {query}\n\n"
            "Use only the provided web research notes. Give a concise answer with 2 or 3 sentences maximum. "
            "If the sources disagree or are incomplete, say so briefly.\n\n"
            + "\n\n---\n\n".join(context_blocks)
        )
        self._emit_state(RuntimeState.SUMMARIZING_SOURCES, "summarizing research")
        answer = self.llm.answer_with_context(query, prompt)
        answer = self._merge_answer_note(answer, evidence_note)
        self._emit_state(RuntimeState.ARCHIVING_SOURCES, "storing research")
        if self.archive_enabled:
            self.archive.store_sources(query, usable_sources, page_content)
            for source in usable_sources:
                content = page_content.get(source.url, "")
                vector = self._embed_text(f"{source.title}\n{source.snippet}\n{content}")
                if vector:
                    self.archive.store_embedding(source.url, vector)
        spoken = self._append_status_notes(f"{answer} I can open the sources if you like.", embedding_note)
        return ResearchResult(query=query, answer=answer, spoken=spoken, sources=usable_sources)

    def recall(self, query: str, limit: int = 3) -> ResearchResult | None:
        embedding_note = self._embedding_status_note()
        hits = self._retrieve_hits(query, limit=limit)
        if not hits:
            return None

        context = "\n\n".join(
            f"Title: {hit.title}\nURL: {hit.url}\nFreshness: {self._freshness_label(hit.age_days, hit.stale)}\nStored summary: {hit.summary}\nStored content: {hit.content[:1500]}"
            for hit in hits
        )
        freshness_note = self._archive_freshness_note(hits)
        answer = self.llm.answer_with_context(
            query,
            (
                f"Question: {query}\n\nUse only the stored local archive notes below. "
                "Answer briefly and mention that this is based on stored research when relevant.\n\n"
                f"{context}"
            ),
        )
        answer = self._merge_answer_note(answer, freshness_note)
        sources = [ResearchSource(title=hit.title, url=hit.url, snippet=hit.summary) for hit in hits]
        spoken = self._append_status_notes(f"From my stored notes: {answer}", embedding_note)
        return ResearchResult(query=query, answer=answer, spoken=spoken, sources=sources, from_archive=True)

    def _retrieve_hits(self, query: str, limit: int) -> list:
        vector = self._embed_text(query)
        if vector:
            semantic_hits = self.archive.semantic_search(vector, limit=limit)
            if semantic_hits:
                return semantic_hits
        return self.archive.search(query, limit=limit)

    def _search_duckduckgo(self, query: str) -> list[ResearchSource]:
        response = self.session.get(f"https://duckduckgo.com/html/?q={quote_plus(query)}", timeout=20)
        response.raise_for_status()
        sources: list[ResearchSource] = []
        blocks = re.findall(r'(<div class="result.*?</div>\s*</div>)', response.text, flags=re.IGNORECASE | re.DOTALL)
        for block in blocks:
            link_match = re.search(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, flags=re.IGNORECASE | re.DOTALL)
            if not link_match:
                continue
            snippet_match = re.search(r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>|<div[^>]+class="result__snippet"[^>]*>(.*?)</div>', block, flags=re.IGNORECASE | re.DOTALL)
            url = html.unescape(link_match.group(1)).strip()
            title = self._clean_text(link_match.group(2))
            snippet_html = (snippet_match.group(1) or snippet_match.group(2)) if snippet_match else ""
            snippet = self._clean_text(snippet_html)
            if url and title:
                sources.append(ResearchSource(title=title, url=url, snippet=snippet))
        return sources

    def _fetch_page_text(self, url: str) -> str:
        try:
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
        except Exception as exc:
            LOGGER.debug("Failed to fetch page %s: %s", url, exc)
            return ""

        text = response.text
        text = re.sub(r"<script.*?</script>", " ", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<style.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<noscript.*?</noscript>", " ", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<svg.*?</svg>", " ", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"\b(cookie|privacy|subscribe|sign up)\b.{0,80}", " ", text, flags=re.IGNORECASE)
        text = self._clean_text(text)
        return text[:6000]

    def _embed_text(self, text: str) -> list[float] | None:
        if not self.embedder:
            return None
        return self.embedder.embed(text)

    def _emit_state(self, state: RuntimeState, reason: str) -> None:
        if self.on_state_change:
            self.on_state_change(state, reason)

    @staticmethod
    def _clean_text(text: str) -> str:
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(text)
        return re.sub(r"\s+", " ", text).strip()

    def _embedding_status_note(self) -> str | None:
        if not self.embedder:
            return None
        if self.embedder.warmed_successfully:
            return None
        if self.embedder.last_error:
            return "Semantic recall is in keyword-only mode because the local embedding model is unavailable."
        return None

    @staticmethod
    def _append_status_notes(spoken: str, *notes: str | None) -> str:
        extras = [note for note in notes if note]
        if not extras:
            return spoken
        return f"{spoken} {' '.join(extras)}"

    @staticmethod
    def _merge_answer_note(answer: str, note: str | None) -> str:
        if not note:
            return answer
        lowered = answer.lower()
        if note.lower() in lowered:
            return answer
        return f"{answer} {note}"

    @classmethod
    def _archive_freshness_note(cls, hits: list) -> str | None:
        if not hits:
            return None
        if all(hit.stale for hit in hits):
            return "These stored notes may be stale."
        if any(hit.stale for hit in hits):
            return "Some of these stored notes are older and may be stale."
        return None

    @classmethod
    def _build_evidence_note(cls, query: str, sources: list[ResearchSource], page_content: dict[str, str]) -> str | None:
        if len(sources) < 2:
            return "This answer is based on limited live evidence."
        if cls._sources_conflict(query, sources, page_content):
            return "The live sources conflict, so treat this answer cautiously."
        return None

    @classmethod
    def _sources_conflict(cls, query: str, sources: list[ResearchSource], page_content: dict[str, str]) -> bool:
        snippets = [
            f"{source.snippet} {page_content.get(source.url, '')[:800]}"
            for source in sources
        ]
        number_sets = [set(re.findall(r"\b\d{1,4}\b", text)) for text in snippets if text]
        if len(number_sets) >= 2:
            common = set.intersection(*number_sets) if all(number_sets) else set()
            all_numbers = set.union(*number_sets)
            if all_numbers and len(all_numbers) >= 2 and len(common) == 0:
                return True

        query_terms = {term for term in re.findall(r"\b[a-z]{4,}\b", query.lower()) if term not in {"what", "when", "where", "with", "from"}}
        if not query_terms:
            return False
        coverage = [len(query_terms & set(re.findall(r"\b[a-z]{4,}\b", text.lower()))) for text in snippets]
        return bool(coverage and min(coverage) == 0 and max(coverage) > 0)

    @staticmethod
    def _freshness_label(age_days: int, stale: bool) -> str:
        if stale:
            return f"stale ({age_days} days old)"
        if age_days == 0:
            return "fresh (today)"
        return f"fresh ({age_days} days old)"
