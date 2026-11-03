from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class ConceptMention(BaseModel):
    concept_name: str
    paper_title: str
    page_number: Optional[int] = None
    context_snippet: str = ""


class ConceptHub(BaseModel):
    name: str
    summary_en: str = ""
    aggregated_score: float = 0.0
    normalized_weight: float = 0.5  # Continuous smooth weight from 0.0 to 1.0
    mentions: List[ConceptMention] = Field(default_factory=list)


class Paper(BaseModel):
    id: str
    title: str
    authors: List[str] = Field(default_factory=list)
    year: Optional[int] = None
    venue: Optional[str] = None
    doi_or_url: Optional[str] = None
    pdf_url: Optional[str] = None
    abstract: str = ""

    # Scientometric metrics
    citation_count: int = 0
    influential_citation_count: int = 0
    citation_velocity: float = 0.0
    influential_ratio: float = 0.0
    objective_scientific_score: float = 0.0
    normalized_weight: float = 0.5  # Continuous smooth weight from 0.0 to 1.0
    is_elbow_selected: bool = False

    # Validation
    topic_relevance_score: float = 0.0
    topic_relevance_reason: str = ""
    requirements_met: bool = False
    requirements_reason: str = ""
    scientific_value_score: float = 0.0

    # Synthesis & Concepts Grounding
    summary_en: str = ""
    key_findings_en: List[str] = Field(default_factory=list)
    methodology_en: str = ""
    limitations_en: str = ""
    extracted_concepts: List[str] = Field(default_factory=list)
    # Raw LLM output kept so concept canonicalization can be re-run on updates
    # without losing concepts that were filtered out earlier.
    extracted_concepts_all: List[str] = Field(default_factory=list)
    concept_mentions: List[ConceptMention] = Field(default_factory=list)

    # Graph connections
    referenced_paper_titles: List[str] = Field(default_factory=list)
    citing_paper_titles: List[str] = Field(default_factory=list)
    related_paper_titles: List[str] = Field(default_factory=list)

    formatted_citation: str = ""


class GraphEdge(BaseModel):
    source_title: str
    target_title: str
    relation_type: str = "relates_to"


class LiteratureBaseState(BaseModel):
    base_id: str
    topic: str
    requirements: str
    citation_format: str
    overall_summary_en: str = ""
    papers: Dict[str, Paper] = Field(default_factory=dict)
    concepts: Dict[str, ConceptHub] = Field(default_factory=dict)
    edges: List[GraphEdge] = Field(default_factory=list)
    bibliography_en: str = ""
    created_at: str = ""
    updated_at: str = ""

    def add_edge(self, edge: GraphEdge) -> bool:
        """Append a graph edge unless an identical one already exists."""
        key = (edge.source_title.strip().lower(), edge.target_title.strip().lower(), edge.relation_type)
        for existing in self.edges:
            if (
                existing.source_title.strip().lower(),
                existing.target_title.strip().lower(),
                existing.relation_type,
            ) == key:
                return False
        self.edges.append(edge)
        return True
