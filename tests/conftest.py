import pytest
from typing import Any, Dict
from lit_graph.llm.base import BaseLLMProvider
from lit_graph.models import Paper


class MockLLMProvider(BaseLLMProvider):
    """Deterministic mock provider for unit tests without network calls."""

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        return "This is a master synthesized overview in English."

    def generate_json(self, prompt: str, system_prompt: str = "") -> Dict[str, Any]:
        # Consolidated 1-step validation response
        if "is_relevant" in prompt or "meets_requirements" in prompt:
            return {
                "is_relevant": True,
                "meets_requirements": True,
                "topic_score": 8.5,
                "reason": "Direct topic match and valid criteria"
            }
        if "keep_paper" in prompt:
            return {"score": 9.0, "reason": "High rigor", "keep_paper": True}
        if "extracted_concepts" in prompt:
            return {
                "summary_en": "Synthesized summary in English.",
                "key_findings_en": ["Key discovery 1", "Empirical speedup"],
                "methodology_en": "Methodology details",
                "limitations_en": "Identified limitations",
                "extracted_concepts": ["Transformers", "Induction Heads"],
                "formatted_citation": "Author, A. (2024). Title of paper."
            }
        if "relations" in prompt:
            return {"relations": []}
        return {}


@pytest.fixture
def mock_llm():
    return MockLLMProvider()


@pytest.fixture
def sample_paper():
    return Paper(
        id="s2_test_sample",
        title="In-context Learning and Induction Heads",
        authors=["Alice Smith", "Bob Jones"],
        year=2023,
        venue="NeurIPS",
        abstract="A mechanistic study on in-context learning circuits in language models.",
        citation_count=120,
        influential_citation_count=15
    )