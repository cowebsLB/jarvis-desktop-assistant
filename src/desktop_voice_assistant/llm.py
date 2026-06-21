from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Protocol

from .capabilities import CapabilityRegistry
from .models import IntentResult

LOGGER = logging.getLogger(__name__)


STYLE_PROMPTS = {
    "stark-butler": (
        "Speak briefly, clearly, and confidently. "
        "Use crisp, formal phrasing and concise status updates. "
        "Use light dry wit sparingly, never ramble, and never sound overly friendly or bubbly. "
        "Short replies are preferred. "
        "You may use phrases such as 'At once', 'Right away', or 'If you like', but do so sparingly. "
    ),
    "concise": (
        "Speak very briefly and directly. "
        "Prefer plain operational language over personality. "
        "Keep replies compact and practical."
    ),
    "neutral": (
        "Speak clearly and helpfully. "
        "Use calm, natural phrasing without roleplay or extra personality. "
        "Keep replies short."
    ),
}


def build_system_prompt(assistant_name: str, assistant_style: str) -> str:
    style_prompt = STYLE_PROMPTS.get(assistant_style, STYLE_PROMPTS["stark-butler"])
    return (
        f"You are {assistant_name}, a polished local desktop voice assistant. "
        f"{style_prompt}"
        "Do not roleplay as any copyrighted character. "
        "If the user asks for unsupported device control, say so plainly and offer the nearest supported action."
    )


def build_routing_system_prompt(assistant_name: str, assistant_style: str) -> str:
    return build_system_prompt(assistant_name, assistant_style) + "\n\n" + CapabilityRegistry().format_for_prompt()


class AssistantLLM(Protocol):
    model: str
    assistant_name: str
    assistant_style: str

    def update_settings(self, *, model: str | None = None, assistant_name: str | None = None, assistant_style: str | None = None) -> None: ...
    def system_prompt(self) -> str: ...
    def answer(self, question: str) -> str: ...
    def answer_with_context(self, question: str, context: str) -> str: ...
    def route_intent(self, transcript: str) -> IntentResult | None: ...


class OllamaAssistant:
    def __init__(self, model: str, assistant_name: str = "Jarvis", assistant_style: str = "stark-butler") -> None:
        self.model = model
        self.assistant_name = assistant_name
        self.assistant_style = assistant_style
        import ollama

        self.client = ollama.Client()

    def update_settings(self, *, model: str | None = None, assistant_name: str | None = None, assistant_style: str | None = None) -> None:
        if model:
            self.model = model
        if assistant_name:
            self.assistant_name = assistant_name
        if assistant_style:
            self.assistant_style = assistant_style

    def system_prompt(self) -> str:
        return build_system_prompt(self.assistant_name, self.assistant_style)

    def answer(self, question: str) -> str:
        LOGGER.info("Sending question to Ollama model=%s", self.model)
        response = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt()},
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
                {"role": "system", "content": self.system_prompt()},
                {"role": "user", "content": context},
                {"role": "user", "content": question},
            ],
            options={"temperature": 0.1},
        )
        return response["message"]["content"].strip()

    def route_intent(self, transcript: str) -> IntentResult | None:
        LOGGER.info("Routing intent via Ollama for transcript: %s", transcript)
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
                    {"role": "system", "content": build_routing_system_prompt(self.assistant_name, self.assistant_style)},
                    {"role": "user", "content": prompt},
                ],
                options={"temperature": 0.0},
            )["message"]["content"].strip()

            LOGGER.info("Ollama intent routing response: %s", response_text)

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
            LOGGER.exception("Failed to route intent via Ollama: %s", exc)
            return None


class GeminiAssistant:
    def __init__(self, model: str, api_key: str, assistant_name: str = "Jarvis", assistant_style: str = "stark-butler") -> None:
        self.model = model
        self.assistant_name = assistant_name
        self.assistant_style = assistant_style
        from google import genai

        self.client = genai.Client(api_key=api_key)
        from google.genai import types

        self._types = types

    def update_settings(self, *, model: str | None = None, assistant_name: str | None = None, assistant_style: str | None = None) -> None:
        if model:
            self.model = model
        if assistant_name:
            self.assistant_name = assistant_name
        if assistant_style:
            self.assistant_style = assistant_style

    def system_prompt(self) -> str:
        return build_system_prompt(self.assistant_name, self.assistant_style)

    def answer(self, question: str) -> str:
        LOGGER.info("Sending question to Gemini model=%s", self.model)
        response = self.client.models.generate_content(
            model=self.model,
            contents=question,
            config=self._types.GenerateContentConfig(
                system_instruction=self.system_prompt(),
                temperature=0.2,
            ),
        )
        return (response.text or "").strip()

    def answer_with_context(self, question: str, context: str) -> str:
        LOGGER.info("Sending contextual question to Gemini model=%s", self.model)
        response = self.client.models.generate_content(
            model=self.model,
            contents=f"Context:\n{context}\n\nQuestion:\n{question}",
            config=self._types.GenerateContentConfig(
                system_instruction=self.system_prompt(),
                temperature=0.1,
            ),
        )
        return (response.text or "").strip()

    def route_intent(self, transcript: str) -> IntentResult | None:
        return None


@dataclass
class ComplexityDecision:
    provider: str
    reason: str


class HybridAssistant:
    def __init__(self, local: AssistantLLM, remote: AssistantLLM | None = None) -> None:
        self.local = local
        self.remote = remote
        self.model = local.model
        self.assistant_name = local.assistant_name
        self.assistant_style = local.assistant_style

    def update_settings(
        self,
        *,
        model: str | None = None,
        assistant_name: str | None = None,
        assistant_style: str | None = None,
        remote_model: str | None = None,
    ) -> None:
        self.local.update_settings(model=model, assistant_name=assistant_name, assistant_style=assistant_style)
        if self.remote:
            self.remote.update_settings(
                model=remote_model or model,
                assistant_name=assistant_name,
                assistant_style=assistant_style,
            )
        self.model = self.local.model
        self.assistant_name = self.local.assistant_name
        self.assistant_style = self.local.assistant_style

    def system_prompt(self) -> str:
        return self.local.system_prompt()

    def answer(self, question: str) -> str:
        decision = self._choose_backend(question, "")
        return self._run_answer(decision, question)

    def answer_with_context(self, question: str, context: str) -> str:
        decision = self._choose_backend(question, context)
        return self._run_answer_with_context(decision, question, context)

    def route_intent(self, transcript: str) -> IntentResult | None:
        return self.local.route_intent(transcript)

    def _run_answer(self, decision: ComplexityDecision, question: str) -> str:
        backend = self.remote if decision.provider == "gemini" else self.local
        if backend is None:
            backend = self.local
        try:
            LOGGER.info("Using %s for answer: %s", decision.provider, decision.reason)
            return backend.answer(question)
        except Exception as exc:
            if backend is self.remote:
                LOGGER.warning("Gemini fallback failed, returning to local model: %s", exc)
                return self.local.answer(question)
            raise

    def _run_answer_with_context(self, decision: ComplexityDecision, question: str, context: str) -> str:
        backend = self.remote if decision.provider == "gemini" else self.local
        if backend is None:
            backend = self.local
        try:
            LOGGER.info("Using %s for contextual answer: %s", decision.provider, decision.reason)
            return backend.answer_with_context(question, context)
        except Exception as exc:
            if backend is self.remote:
                LOGGER.warning("Gemini contextual fallback failed, returning to local model: %s", exc)
                return self.local.answer_with_context(question, context)
            raise

    def _choose_backend(self, question: str, context: str) -> ComplexityDecision:
        if not self.remote:
            return ComplexityDecision("local", "Gemini fallback unavailable")
        if self._is_complex(question, context):
            return ComplexityDecision("gemini", "request scored as complex")
        return ComplexityDecision("local", "request scored as simple")

    @staticmethod
    def _is_complex(question: str, context: str) -> bool:
        combined = f"{question}\n{context}".lower()
        if len(context) > 1800:
            return True
        if len(question) > 220:
            return True
        signals = [
            "compare",
            "tradeoff",
            "trade-off",
            "analyze",
            "analysis",
            "architecture",
            "refactor",
            "strategy",
            "step by step",
            "in detail",
            "detailed",
            "pros and cons",
            "draft",
            "write a",
            "plan",
            "summarize this page",
        ]
        hits = sum(1 for signal in signals if signal in combined)
        return hits >= 1 or combined.count("?") > 1
