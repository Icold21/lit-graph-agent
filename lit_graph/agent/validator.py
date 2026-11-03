from typing import Any

from ..llm.base import BaseLLMProvider
from ..llm.prompts import SYSTEM_REVIEWER, validation_prompt
from ..models import Paper
from ..utils.logging_setup import get_logger

logger = get_logger(__name__)


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class LiteratureValidator:
    """Fast consolidated scientific and requirements validation pipeline."""

    def __init__(self, llm: BaseLLMProvider):
        self.llm = llm

    def validate_candidate(self, paper: Paper, topic: str, requirements: str) -> bool:
        """Consolidated 1-step validation: checks topic relevance and requirements together."""
        prompt = validation_prompt(
            topic,
            requirements,
            paper.title,
            paper.year,
            paper.venue,
            paper.abstract,
        )
        res = self.llm.generate_json(prompt, SYSTEM_REVIEWER)
        if not isinstance(res, dict):
            logger.warning(
                "Validation returned %s instead of an object for %r; rejecting",
                type(res).__name__,
                paper.title,
            )
            paper.topic_relevance_reason = "Validator returned malformed JSON"
            return False

        paper.topic_relevance_score = _to_float(res.get("topic_score"))
        paper.topic_relevance_reason = str(res.get("reason") or "No reason provided")
        paper.requirements_met = bool(res.get("meets_requirements", False))
        is_relevant = bool(res.get("is_relevant", False))
        return is_relevant and paper.requirements_met
