import json
import re
from typing import Any, Dict
from openai import OpenAI
from .base import BaseLLMProvider


class UniversalLLMProvider(BaseLLMProvider):
    """
    Universal model-agnostic provider.
    Supports DeepSeek, OpenAI, Groq, OpenRouter, Ollama, vLLM, and any OpenAI-compatible API.
    """

    def __init__(self, api_key: str, model_name: str, base_url: str):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model_name

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0.2,
        )
        return (response.choices[0].message.content or "").strip()

    def generate_json(self, prompt: str, system_prompt: str = "") -> Dict[str, Any]:
        sys = (
            system_prompt + "\nRespond strictly in valid JSON format without commentary or markdown code blocks."
        ) if system_prompt else "Respond strictly in valid JSON format."

        raw_output = self.generate(prompt, sys)
        return self._sanitize_and_parse_json(raw_output)

    @staticmethod
    def _sanitize_and_parse_json(raw_text: str) -> Dict[str, Any]:
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

        # 4. Fallback: extract the largest valid JSON substring between '{' and '}'
        start_idx = text.find("{")
        end_idx = text.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            try:
                return json.loads(text[start_idx : end_idx + 1])
            except json.JSONDecodeError:
                pass

        return {}