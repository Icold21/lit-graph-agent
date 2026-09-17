import pytest
from typing import Any, Dict
from lit_graph.llm.base import BaseLLMProvider
from lit_graph.models import Paper


class MockLLMProvider(BaseLLMProvider):
    """Deterministic mock provider for unit tests without network calls."""

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        return "This is a master synthesized overview in English."

    def generate_json(self, prompt: str, system_prompt: str = "") -> Dict[str, Any]:
        if "is_relevant" in prompt or "meets_requirements" in prompt:
            return {
                "is_relevant": True,
                "meets_requirements": True,
                "topic_score": 8.5,
                "reason": "Direct topic match and valid criteria"
            }
        if "definitions" in prompt or "Target Concepts to define" in prompt:
            return {
                "definitions": {
                    "Transformers": "A deep neural architecture based on self-attention mechanisms.",
                    "Induction Heads": "A two-layer circuit mechanism that performs in-context copy operations."
                }
            }
        if "master_bibliography_text" in prompt:
            return {
                "citations": [{"id": "s2_test_sample", "formatted_string": "1. Alice Smith (2023). In-context Learning."}],
                "master_bibliography_text": "1. Alice Smith (2023). In-context Learning."
            }
        if "extracted_concepts" in prompt:
            return {
                "summary_en": "Synthesized summary in English.",
                "key_findings_en": ["Key discovery 1", "Empirical speedup"],
                "methodology_en": "Methodology details",
                "limitations_en": "Identified limitations",
                "extracted_concepts": ["Transformers", "Induction Heads"]
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