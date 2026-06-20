from __future__ import annotations

import logging


LOGGER = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self, model: str) -> None:
        self.model = model
        import ollama

        self.client = ollama.Client()

    def embed(self, text: str) -> list[float] | None:
        cleaned = text.strip()
        if not cleaned:
            return None
        try:
            response = self.client.embed(model=self.model, input=cleaned[:4000])
        except Exception as exc:
            LOGGER.debug("Embedding request failed for model=%s: %s", self.model, exc)
            return None

        vectors = response.get("embeddings") or []
        if vectors and isinstance(vectors[0], list):
            return [float(value) for value in vectors[0]]
        embedding = response.get("embedding")
        if embedding:
            return [float(value) for value in embedding]
        return None
