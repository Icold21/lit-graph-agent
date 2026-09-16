from typing import List
from ..llm.base import BaseLLMProvider
from ..models import Paper


class LiteratureValidator:
    """Fast consolidated scientific and requirements validation pipeline."""

    def __init__(self, llm: BaseLLMProvider):
        self.llm = llm

    def validate_candidate(self, paper: Paper, topic: str, requirements: str) -> bool:
        """Consolidated 1-step validation: checks topic relevance and requirements together."""
        prompt = f"""
Topic: {topic}
Requirements: {requirements}

Paper to Evaluate:
Title: {paper.title}
Year: {paper.year or 'Unknown'}
Venue: {paper.venue or 'Unknown'}
Abstract: {paper.abstract[:700]}

Evaluate strictly in JSON format:
{{
  "is_relevant": true,
  "meets_requirements": true,
  "topic_score": 8.5,
  "reason": "Concise 1-sentence explanation in English"
}}
"""
        res = self.llm.generate_json(prompt, "Scientific reviewer. Output only valid JSON.")
        
        paper.topic_relevance_score = float(res.get("topic_score", 0.0))
        paper.topic_relevance_reason = res.get("reason", "No reason provided")
        paper.requirements_met = bool(res.get("meets_requirements", False))
        
        is_relevant = bool(res.get("is_relevant", False))
        return is_relevant and paper.requirements_met

    def validate_stage_3_scientific_value(self, paper: Paper, existing_papers: List[Paper]) -> bool:
        """Fast redundancy check."""
        existing_titles = [p.title for p in existing_papers]
        prompt = f"""
Paper Title: {paper.title}
Abstract: {paper.abstract[:600]}
Existing Titles in Knowledge Base: {existing_titles}

Evaluate in JSON:
{{
  "score": 8.0,
  "keep_paper": true
}}
"""
        res = self.llm.generate_json(prompt, "Senior editor. Output only JSON.")
        paper.scientific_value_score = float(res.get("score", 7.5))
        return bool(res.get("keep_paper", True))