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
        on_state_change=None,
    ) -> None:
        self.llm = llm
        self.archive = archive
        self.fetch_limit = fetch_limit
        self.embedder = embedder
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
        self._emit_state(RuntimeState.RESEARCHING, "starting web research")
        pages = self._search_duckduckgo(query)
        if not pages:
            archive_result = self.recall(query)
            if archive_result:
                return archive_result
            return ResearchResult(query=query, answer="No useful web results were found.", spoken="I couldn't find useful web results.")

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
            return ResearchResult(query=query, answer="The pages loaded poorly, so I don't have a reliable answer yet.", spoken="The pages loaded poorly, so I don't have a reliable answer yet.")

        self._emit_state(RuntimeState.RANKING_SOURCES, "ranking source pages")
        prompt = (
            f"Question: {query}\n\n"
            "Use only the provided web research notes. Give a concise answer with 2 or 3 sentences maximum. "
            "If the sources disagree or are incomplete, say so briefly.\n\n"
            + "\n\n---\n\n".join(context_blocks)
        )
        self._emit_state(RuntimeState.SUMMARIZING_SOURCES, "summarizing research")
        answer = self.llm.answer_with_context(query, prompt)
        self._emit_state(RuntimeState.ARCHIVING_SOURCES, "storing research")
        self.archive.store_sources(query, usable_sources, page_content)
        for source in usable_sources:
            content = page_content.get(source.url, "")
            vector = self._embed_text(f"{source.title}\n{source.snippet}\n{content}")
            if vector:
                self.archive.store_embedding(source.url, vector)
        spoken = f"{answer} I can open the sources if you like."
        return ResearchResult(query=query, answer=answer, spoken=spoken, sources=usable_sources)

    def recall(self, query: str, limit: int = 3) -> ResearchResult | None:
        hits = self._retrieve_hits(query, limit=limit)
        if not hits:
            return None

        context = "\n\n".join(
            f"Title: {hit.title}\nURL: {hit.url}\nStored summary: {hit.summary}\nStored content: {hit.content[:1500]}"
            for hit in hits
        )
        answer = self.llm.answer_with_context(
            query,
            (
                f"Question: {query}\n\nUse only the stored local archive notes below. "
                "Answer briefly and mention that this is based on stored research when relevant.\n\n"
                f"{context}"
            ),
        )
        sources = [ResearchSource(title=hit.title, url=hit.url, snippet=hit.summary) for hit in hits]
        spoken = f"From my stored notes: {answer}"
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
