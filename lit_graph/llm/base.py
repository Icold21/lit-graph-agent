from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseLLMProvider(ABC):
    """Abstract interface for LLM backends."""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """Generates plain text response."""
        pass

    @abstractmethod
    def generate_json(self, prompt: str, system_prompt: str = "") -> Dict[str, Any]:
        """Generates structured JSON response."""
        pass