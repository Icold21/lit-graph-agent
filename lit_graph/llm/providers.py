import json
import re
import time
from typing import Any

from openai import OpenAI

from ..config import settings
from ..utils.cache import get_cache
from ..utils.logging_setup import get_logger
from .base import BaseLLMProvider

logger = get_logger(__name__)


class UniversalLLMProvider(BaseLLMProvider):
    """
    Universal model-agnostic provider.
    Supports DeepSeek, OpenAI, Groq, OpenRouter, Ollama, vLLM, and any OpenAI-compatible API.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str,
        base_url: str,
        timeout: float | None = None,
        max_retries: int | None = None,
    ):
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout or settings.llm_timeout)
        self.model_name = model_name
        self.max_retries = max(1, max_retries or settings.llm_max_retries)
        self._cache = get_cache()

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        cache_key = ("generate", self.model_name, system_prompt, prompt)
        if settings.llm_cache_enabled:
            cached = self._cache.get("llm", cache_key)
            if isinstance(cached, str):
                return cached

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=0.2,
                )
                content = (response.choices[0].message.content or "").strip()
                if settings.llm_cache_enabled:
                    self._cache.set("llm", cache_key, content)
                return content
            except Exception as exc:  # noqa: BLE001 - provider SDK raises many types
                last_error = exc
                delay = min(2**attempt, 10)
                logger.warning(
                    "LLM request failed (attempt %s/%s): %s",
                    attempt + 1,
                    self.max_retries,
                    exc,
                )
                if attempt + 1 < self.max_retries:
                    time.sleep(delay)

        raise RuntimeError(f"LLM request failed after {self.max_retries} attempts: {last_error}") from last_error

    def generate_json(self, prompt: str, system_prompt: str = "") -> Any:
        sys = (
            system_prompt + "\nRespond strictly in valid JSON format without commentary or markdown code blocks."
        ) if system_prompt else "Respond strictly in valid JSON format."

        raw_output = self.generate(prompt, sys)
        parsed = self._sanitize_and_parse_json(raw_output)
        if parsed in ({}, [], None, ""):
            logger.warning(
                "LLM returned empty or unparsable JSON (model=%s, %s chars). First 160 chars: %r",
                self.model_name,
                len(raw_output),
                raw_output[:160],
            )
        return parsed

    @staticmethod
    def _sanitize_and_parse_json(raw_text: str) -> Any:
        """Sanitizer for reasoning models (DeepSeek R1, QwQ) and raw LLM text."""
        # 1. Strip reasoning/thinking tags (<think>...</think> or <thought>...</thought>)
        text = re.sub(r"<(think|thought)>[\s\S]*?</\1>", "", raw_text).strip()

        # 2. Extract from markdown code fences if present
        codeblock_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if codeblock_match:
            text = codeblock_match.group(1).strip()

        # 3. Direct JSON parsing
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 4. Fallback: extract the largest valid JSON substring.
        # Prefer an object, then an array.
        for open_char, close_char in (("{", "}"), ("[", "]")):
            start_idx = text.find(open_char)
            end_idx = text.rfind(close_char)
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                try:
                    return json.loads(text[start_idx : end_idx + 1])
                except json.JSONDecodeError:
                    continue

        return {}
