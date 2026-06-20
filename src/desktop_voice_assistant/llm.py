from __future__ import annotations

import logging

LOGGER = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "You are a polished local desktop voice assistant with a Stark-style butler-tech tone. "
    "Speak briefly, clearly, and confidently. "
    "Use crisp, formal phrasing and concise status updates. "
    "Use light dry wit sparingly, never ramble, and never sound overly friendly or bubbly. "
    "Short replies are preferred. "
    "You may use phrases such as 'At once', 'Right away', or 'If you like', but do so sparingly. "
    "Do not roleplay as any copyrighted character. "
    "If the user asks for unsupported device control, say so plainly and offer the nearest supported action."
)


class OllamaAssistant:
    def __init__(self, model: str) -> None:
        self.model = model
        import ollama

        self.client = ollama.Client()

    def answer(self, question: str) -> str:
        LOGGER.info("Sending question to Ollama model=%s", self.model)
        response = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
            options={"temperature": 0.2},
        )
        return response["message"]["content"].strip()

    def answer_with_context(self, question: str, context: str) -> str:
        LOGGER.info("Sending contextual question to Ollama model=%s", self.model)
        response = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": context},
                {"role": "user", "content": question},
            ],
            options={"temperature": 0.1},
        )
        return response["message"]["content"].strip()
