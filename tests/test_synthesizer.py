import re
from typing import Any, List

from lit_graph.agent.synthesizer import LiteratureSynthesizer
from lit_graph.config import settings
from lit_graph.models import ConceptHub, LiteratureBaseState, Paper


class CountingLLM:
    def __init__(self) -> None:
        self.json_calls: List[str] = []

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        return "overview"

    def generate_json(self, prompt: str, system_prompt: str = "") -> Any:
        self.json_calls.append(prompt)
        if "Target Concepts to define" in prompt:
            match = re.search(r"Target Concepts to define:\s*(\[[^\]]*\])", prompt, re.S)
            names = re.findall(r"'([^']+)'", match.group(1)) if match else []
            return {"definitions": {name: f"Definition for {name}." for name in names}}
        if "Selected Papers Metadata" in prompt:
            return {"citations": []}
        return {}


def _state(concept_count: int) -> LiteratureBaseState:
    paper = Paper(
        id="p1",
        title="Paper One",
        authors=["Alice Smith"],
        year=2024,
        abstract="Abstract",
        summary_en="Summary",
        extracted_concepts=["Transformers"],
        formatted_citation="Smith, A. (2024). Paper One.",
    )
    concepts = {
        f"Concept {index}": ConceptHub(name=f"Concept {index}", mentions=[])
        for index in range(concept_count)
    }
    return LiteratureBaseState(
        base_id="b",
        topic="Topic",
        requirements="None",
        citation_format="APA 7th",
        papers={paper.id: paper},
        concepts=concepts,
    )


def test_concept_definitions_are_batched(monkeypatch):
    monkeypatch.setattr(settings, "concept_batch_size", 10)
    llm = CountingLLM()
    synthesizer = LiteratureSynthesizer(llm)
    state = _state(25)

    synthesizer.synthesize_all_concept_hubs_batch(state)

    assert len(llm.json_calls) == 3
    assert all(hub.summary_en.startswith("Definition for") for hub in state.concepts.values())
    assert all(hub.summary_en for hub in state.concepts.values())


def test_existing_definitions_are_not_regenerated(monkeypatch):
    monkeypatch.setattr(settings, "concept_batch_size", 10)
    llm = CountingLLM()
    synthesizer = LiteratureSynthesizer(llm)
    state = _state(3)
    state.concepts["Concept 0"].summary_en = "Already defined"

    synthesizer.synthesize_all_concept_hubs_batch(state)

    assert state.concepts["Concept 0"].summary_en == "Already defined"
    assert len(llm.json_calls) == 1


def test_bibliography_falls_back_when_llm_returns_nothing(monkeypatch):
    monkeypatch.setattr(settings, "bibliography_batch_size", 20)
    llm = CountingLLM()
    synthesizer = LiteratureSynthesizer(llm)
    state = _state(1)
    state.papers["p1"].formatted_citation = ""

    synthesizer.harmonize_master_bibliography(state)

    assert state.papers["p1"].formatted_citation
    assert state.bibliography_en.strip()


def test_bibliography_is_batched(monkeypatch):
    monkeypatch.setattr(settings, "bibliography_batch_size", 10)
    llm = CountingLLM()
    synthesizer = LiteratureSynthesizer(llm)
    state = _state(1)
    state.papers = {
        f"p{index}": Paper(
            id=f"p{index}",
            title=f"Paper {index}",
            authors=[f"Author {index}"],
            year=2024,
            formatted_citation="",
        )
        for index in range(25)
    }

    synthesizer.harmonize_master_bibliography(state)

    assert len([call for call in llm.json_calls if "Selected Papers Metadata" in call]) == 3
    assert all(paper.formatted_citation for paper in state.papers.values())
