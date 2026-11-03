import ast
import re
from typing import Any, Dict, List

import pytest

from lit_graph.llm.base import BaseLLMProvider
from lit_graph.models import Paper


class MockLLMProvider(BaseLLMProvider):
    """Deterministic mock provider for unit tests without network calls."""

    def __init__(self) -> None:
        self.calls: List[str] = []

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        self.calls.append(prompt)
        return "This is a master synthesized overview in English."

    def generate_json(self, prompt: str, system_prompt: str = "") -> Any:
        self.calls.append(prompt)
        if "routing an academic literature retrieval task" in prompt:
            return {
                "primary": ["arxiv"],
                "fallback": ["semantic_scholar"],
                "rationale": "Recent interpretability work lives on arXiv first.",
                "confidence": 0.9,
            }
        if "Generate 2 distinct academic search queries" in prompt:
            return {"queries": ["latent circuits", "attention head interpretability"]}
        if "Paper to Evaluate" in prompt:
            return {
                "is_relevant": True,
                "meets_requirements": True,
                "topic_score": 8.5,
                "reason": "Direct topic match and valid criteria",
            }
        if "Target Concepts to define" in prompt:
            match = re.search(r"Target Concepts to define:\s*(\[[^\]]*\])", prompt, re.S)
            names: List[str] = []
            if match:
                try:
                    parsed = ast.literal_eval(match.group(1))
                    if isinstance(parsed, list):
                        names = [str(name) for name in parsed]
                except (ValueError, SyntaxError):
                    names = []
            return {"definitions": {name: f"A concise definition of {name} grounded in the sources." for name in names}}
        if "Selected Papers Metadata" in prompt:
            return {"citations": []}
        if "conceptual cross-links" in prompt:
            return {"relations": []}
        if "Synthesize the following paper" in prompt:
            return {
                "summary_en": "Synthesized summary in English.",
                "key_findings_en": ["Key discovery 1", "Empirical speedup"],
                "methodology_en": "Methodology details",
                "limitations_en": "Identified limitations",
                "extracted_concepts": ["Transformers", "Induction Heads", "transformers"],
            }
        if "Target Concepts:" in prompt and "mentions" in prompt:
            return {"mentions": [], "updated_running_summary": "Recap so far."}
        return {}


class FakeSearchEngine:
    """In-memory stand-in for AcademicSearchEngine used by integration tests."""

    def __init__(self, candidates: List[Dict[str, Any]] | None = None):
        self.candidates = candidates or []
        self.calls: List[Dict[str, Any]] = []

    def set_candidates(self, candidates: List[Dict[str, Any]]) -> None:
        self.candidates = candidates

    def available_engines(self) -> List[str]:
        return ["semantic_scholar", "arxiv", "web"]

    def search_and_rank(
        self,
        query: str,
        top_k: int = 25,
        engines: List[str] | None = None,
        fallback_engines: List[str] | None = None,
        min_results: int = 5,
    ) -> List[Dict[str, Any]]:
        self.calls.append(
            {
                "query": query,
                "top_k": top_k,
                "engines": list(engines) if engines else None,
                "fallback_engines": list(fallback_engines) if fallback_engines else None,
                "min_results": min_results,
            }
        )
        return [dict(candidate) for candidate in self.candidates][:top_k]

    def expand_citations(self, paper_id: str, limit: int = 3) -> Dict[str, List[str]]:
        return {"references": [], "citations": []}


def make_candidate(index: int, year: int = 2024) -> Dict[str, Any]:
    return {
        "id": f"fake_{index}",
        "title": f"Mechanistic Interpretability Study {index}",
        "authors": [f"Author {index}"],
        "year": year,
        "venue": "NeurIPS",
        "doi_or_url": f"https://example.org/paper/{index}.pdf",
        "pdf_url": None,
        "abstract": f"Abstract {index} about circuits and induction heads.",
        "citation_count": 10 * index,
        "influential_citation_count": index,
    }


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
        influential_citation_count=15,
    )


@pytest.fixture
def fake_search_engine():
    return FakeSearchEngine([make_candidate(index) for index in range(1, 6)])
