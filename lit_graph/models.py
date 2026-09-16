from typing import List, Dict, Optional, Set
from pydantic import BaseModel, Field


class Paper(BaseModel):
    id: str
    title: str
    authors: List[str] = Field(default_factory=list)
    year: Optional[int] = None
    venue: Optional[str] = None
    doi_or_url: Optional[str] = None
    abstract: str = ""
    
    # Raw Academic Metrics
    citation_count: int = 0
    influential_citation_count: int = 0
    
    # Objective Calculated Scientific Metrics
    citation_velocity: float = 0.0          # Citations / Year
    influential_ratio: float = 0.0          # Influential / Total
    objective_scientific_score: float = 0.0 # Composite Scientometric Score
    is_elbow_selected: bool = False
    
    # 3-Stage LLM Validation
    topic_relevance_score: float = 0.0
    topic_relevance_reason: str = ""
    requirements_met: bool = False
    requirements_reason: str = ""
    scientific_value_score: float = 0.0
    scientific_value_reason: str = ""
    
    # English Knowledge Synthesis
    summary_en: str = ""
    key_findings_en: List[str] = Field(default_factory=list)
    methodology_en: str = ""
    limitations_en: str = ""
    extracted_concepts: List[str] = Field(default_factory=list)
    
    # Citation Graph Connections
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
    concepts: Set[str] = Field(default_factory=set)
    edges: List[GraphEdge] = Field(default_factory=list)
    bibliography_en: str = ""
    created_at: str = ""
    updated_at: str = ""