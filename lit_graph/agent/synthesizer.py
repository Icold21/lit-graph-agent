import json
from ..llm.base import BaseLLMProvider
from ..models import Paper, GraphEdge, LiteratureBaseState


class LiteratureSynthesizer:
    """Synthesizes individual paper cards, concepts, cross-links, and bibliographies strictly in English."""

    def __init__(self, llm: BaseLLMProvider):
        self.llm = llm

    def synthesize_paper(self, paper: Paper, citation_format: str) -> None:
        prompt = f"""
Synthesize the following paper strictly in English:
Title: {paper.title}
Authors: {', '.join(paper.authors)}
Year: {paper.year}
Venue: {paper.venue}
URL/DOI: {paper.doi_or_url}
Abstract: {paper.abstract}
Target Citation Format: {citation_format}

Return strict JSON:
{{
  "summary_en": "Deep single-paragraph synthesis of the research and contributions in English",
  "key_findings_en": ["Key finding 1", "Key finding 2", "Key finding 3"],
  "methodology_en": "Methodology summary in English",
  "limitations_en": "Limitations identified in English",
  "extracted_concepts": ["Concept 1", "Concept 2", "Concept 3"],
  "formatted_citation": "Properly formatted citation strictly following {citation_format} style"
}}
"""
        res = self.llm.generate_json(prompt, "Academic literature synthesizer. Output only in English.")
        paper.summary_en = res.get("summary_en", "")
        paper.key_findings_en = res.get("key_findings_en", [])
        paper.methodology_en = res.get("methodology_en", "")
        paper.limitations_en = res.get("limitations_en", "")
        paper.extracted_concepts = res.get("extracted_concepts", [])
        paper.formatted_citation = res.get(
            "formatted_citation",
            f"{', '.join(paper.authors)} ({paper.year}). {paper.title}."
        )

    def link_paper_network(self, state: LiteratureBaseState) -> None:
        papers = list(state.papers.values())
        if len(papers) < 2:
            return

        summaries = [{"title": p.title, "summary": p.summary_en, "concepts": p.extracted_concepts} for p in papers]
        prompt = f"""
Analyze these papers and identify conceptual and relational connections:
{json.dumps(summaries, indent=2)}

Return strict JSON with list:
{{"relations": [{{"source_title": "Title A", "target_title": "Title B", "relation": "builds_upon"}}]}}
"""
        res = self.llm.generate_json(prompt, "Citation network analyzer.")
        for rel in res.get("relations", []):
            src_title = rel.get("source_title", "")
            tgt_title = rel.get("target_title", "")

            src = next((p for p in papers if p.title.lower() == src_title.lower()), None)
            tgt = next((p for p in papers if p.title.lower() == tgt_title.lower()), None)
            if src and tgt and src.id != tgt.id:
                if tgt.title not in src.related_paper_titles:
                    src.related_paper_titles.append(tgt.title)
                state.edges.append(GraphEdge(
                    source_title=src.title,
                    target_title=tgt.title,
                    relation_type=rel.get("relation", "relates_to")
                ))

    def build_overall_synthesis(self, state: LiteratureBaseState) -> None:
        papers = list(state.papers.values())
        if not papers:
            state.overall_summary_en = "No verified literature found."
            state.bibliography_en = "No bibliography."
            return

        # Sort papers alphabetically by first author's name or title
        def get_sort_key(p: Paper) -> str:
            if p.authors:
                return p.authors[0].split()[-1].lower()
            return p.title.lower()

        sorted_papers = sorted(papers, key=get_sort_key)

        summaries = [f"- **{p.title}** ({p.year}): {p.summary_en}" for p in sorted_papers]
        prompt = f"""
Topic: {state.topic}
Requirements: {state.requirements}

Synthesize these {len(sorted_papers)} accepted academic papers into a master literature review in English:
{chr(10).join(summaries)}

Structure:
1. Executive Summary & Research Consensus
2. Methodological Landscapes & Divergence
3. Research Gaps & Strategic Outlook
"""
        state.overall_summary_en = self.llm.generate(prompt, "Academic literature review author. Write strictly in English.")

        # Master clean bibliography list
        is_bibtex = "bibtex" in state.citation_format.lower()
        if is_bibtex:
            state.bibliography_en = "\n\n".join([p.formatted_citation for p in sorted_papers])
        else:
            state.bibliography_en = "\n\n".join([f"{i+1}. {p.formatted_citation}" for i, p in enumerate(sorted_papers)])