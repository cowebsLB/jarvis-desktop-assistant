import json
import logging
import re

from .capabilities import CapabilityRegistry
from .models import IntentResult

LOGGER = logging.getLogger(__name__)


BASE_SYSTEM_PROMPT = (
    "You are a polished local desktop voice assistant with a Stark-style butler-tech tone. "
    "Speak briefly, clearly, and confidently. "
    "Use crisp, formal phrasing and concise status updates. "
    "Use light dry wit sparingly, never ramble, and never sound overly friendly or bubbly. "
    "Short replies are preferred. "
    "You may use phrases such as 'At once', 'Right away', or 'If you like', but do so sparingly. "
    "Do not roleplay as any copyrighted character. "
    "If the user asks for unsupported device control, say so plainly and offer the nearest supported action."
)

SYSTEM_PROMPT = BASE_SYSTEM_PROMPT + "\n\n" + CapabilityRegistry().format_for_prompt()


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

    def route_intent(self, transcript: str) -> IntentResult | None:
        LOGGER.info("Routing intent via LLM for transcript: %s", transcript)
        prompt = (
            "Understand the following user command and route it to the appropriate intent and slots from the Capabilities Registry.\n"
            "If it does not match any specific desktop intent, or is unsupported, return \"unsupported\" as the intent.\n\n"
            f"User command: \"{transcript}\"\n\n"
            "Return ONLY a valid JSON object of format:\n"
            '{"intent": "<intent_name>", "slots": {<slot_key>: <slot_value>}}'
        )

        try:
            response_text = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                options={"temperature": 0.0},
            )["message"]["content"].strip()

            LOGGER.info("LLM intent routing response: %s", response_text)

            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if not json_match:
                return None

            data = json.loads(json_match.group(0))
            intent_name = data.get("intent")
            slots = data.get("slots", {})
            if not intent_name:
                return None
            return IntentResult(intent_name, 0.9, slots)
        except Exception as exc:
            LOGGER.exception("Failed to route intent via LLM: %s", exc)
            return None

