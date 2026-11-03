from abc import ABC, abstractmethod
from typing import Any

from ..utils.logging_setup import get_logger

logger = get_logger(__name__)


class BaseLLMProvider(ABC):
    """Abstract interface for LLM backends."""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """Generates plain text response."""
        pass

    @abstractmethod
    def generate_json(self, prompt: str, system_prompt: str = "") -> Any:
        """Generates structured JSON response (object or array)."""
        pass
