from __future__ import annotations

import logging


LOGGER = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self, model: str) -> None:
        self.model = model
        self._last_error: str | None = None
        self._warmed_successfully = False
        import ollama

        self.client = ollama.Client()

    def embed(self, text: str) -> list[float] | None:
        cleaned = text.strip()
        if not cleaned:
            return None
        try:
            response = self.client.embed(model=self.model, input=cleaned[:4000])
        except Exception as exc:
            self._last_error = str(exc)
            LOGGER.debug("Embedding request failed for model=%s: %s", self.model, exc)
            return None

        vectors = response.get("embeddings") or []
        if vectors and isinstance(vectors[0], list):
            self._last_error = None
            self._warmed_successfully = True
            return [float(value) for value in vectors[0]]
        embedding = response.get("embedding")
        if embedding:
            self._last_error = None
            self._warmed_successfully = True
            return [float(value) for value in embedding]
        return None

    def warmup(self) -> bool:
        return self.embed("warmup") is not None

    @property
    def last_error(self) -> str | None:
        return self._last_error

    @property
    def warmed_successfully(self) -> bool:
        return self._warmed_successfully

    def status_summary(self) -> str:
        if self._warmed_successfully:
            return f"Embedding model {self.model} is ready."
        if self._last_error:
            return f"Embedding model {self.model} is degraded: {self._last_error}"
        return f"Embedding model {self.model} has not been warmed yet."
