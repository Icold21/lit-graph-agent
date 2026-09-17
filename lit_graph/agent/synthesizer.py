import json
from typing import List, Dict
from ..llm.base import BaseLLMProvider
from ..models import Paper, GraphEdge, LiteratureBaseState, ConceptMention, ConceptHub


class LiteratureSynthesizer:
    """Synthesizes paper notes, batch-defines concept hubs, and harmonizes bibliographies."""

    def __init__(self, llm: BaseLLMProvider):
        self.llm = llm

    def synthesize_paper_content(self, paper: Paper) -> None:
        """Extracts executive summary, methodology, and key concepts in 1 fast LLM call."""
        prompt = f"""
Synthesize the following paper strictly in English:
Title: {paper.title}
Authors: {', '.join(paper.authors)}
Year: {paper.year}
Venue: {paper.venue}
Abstract: {paper.abstract}

Return strict JSON:
{{
  "summary_en": "Deep single-paragraph executive summary in English",
  "key_findings_en": ["Key finding 1", "Key finding 2", "Key finding 3"],
  "methodology_en": "Methodology summary in English",
  "limitations_en": "Limitations identified in English",
  "extracted_concepts": ["Concept 1", "Concept 2", "Concept 3"]
}}
"""
        res = self.llm.generate_json(prompt, "Academic literature synthesizer. Output only valid JSON.")
        paper.summary_en = res.get("summary_en", "")
        paper.key_findings_en = res.get("key_findings_en", [])
        paper.methodology_en = res.get("methodology_en", "")
        paper.limitations_en = res.get("limitations_en", "")
        paper.extracted_concepts = res.get("extracted_concepts", [])

    def synthesize_all_concept_hubs_batch(self, state: LiteratureBaseState) -> None:
        """
        FAST SINGLE-PASS SYNTHESIS: Generates concise encyclopedic definitions for ALL
        concepts simultaneously in ONE call, turning 15+ calls into 1.
        """
        if not state.concepts:
            return

        concept_names = list(state.concepts.keys())
        paper_context = [
            {"title": p.title, "year": p.year, "summary": p.summary_en[:200], "concepts": p.extracted_concepts}
            for p in state.papers.values()
        ]

        prompt = f"""
Domain Topic: "{state.topic}"
Target Concepts to define: {concept_names}

Referenced Sources Context:
{json.dumps(paper_context, indent=2)}

Task:
For EACH concept in the list, write a concise 2-sentence authoritative definition explaining its core role and consensus.
Return strict JSON mapping concept names to definitions:
{{
  "definitions": {{
    "Concept Name": "2-sentence authoritative definition and context..."
  }}
}}
"""
        res = self.llm.generate_json(prompt, "Academic encyclopedist. Return only valid JSON.")
        defs = res.get("definitions", {})

        for c_name, hub in state.concepts.items():
            matched_def = defs.get(c_name)
            if not matched_def:
                matched_def = next((v for k, v in defs.items() if k.lower() == c_name.lower()), "")
            hub.summary_en = matched_def or f"Key conceptual node referenced across {len(hub.mentions) or 1} literature sources."

    def ground_concepts_to_pages(self, paper: Paper, pages_dict: Dict[int, str], batch_size: int = 3) -> None:
        """Deep scanning (Used only when --deep flag is enabled)."""
        if not pages_dict or not paper.extracted_concepts:
            return

        page_numbers = sorted(pages_dict.keys())
        target_concepts_lower = {c.lower(): c for c in paper.extracted_concepts}
        running_summary = f"Abstract: {paper.abstract[:250]}..." if paper.abstract else "Beginning of manuscript."

        for i in range(0, len(page_numbers), batch_size):
            batch_pages = page_numbers[i : i + batch_size]
            batch_payload = {p_num: pages_dict[p_num] for p_num in batch_pages}

            prompt = f"""
Paper Title: "{paper.title}"
Target Concepts: {paper.extracted_concepts}

[Context Anchor]: "{paper.abstract[:200]}"
[Running Context]: "{running_summary}"
[Pages {batch_pages[0]}-{batch_pages[-1]}]:
{json.dumps(batch_payload, indent=2)}

Task:
Scan these pages. If NONE of the target concepts are mentioned, return [].
Return strict JSON:
{{
  "mentions": [
    {{
      "concept_name": "Exact concept name",
      "page_number": {batch_pages[0]},
      "context_snippet": "1-sentence quotation"
    }}
  ],
  "updated_running_summary": "2-sentence recap up to page {batch_pages[-1]}"
}}
"""
            res = self.llm.generate_json(prompt, "Accurate concept indexer. Strict JSON.")
            if res.get("updated_running_summary"):
                running_summary = res.get("updated_running_summary")

            for item in res.get("mentions", []):
                c_name_raw = item.get("concept_name", "").strip()
                matched_concept = target_concepts_lower.get(c_name_raw.lower())
                page_num = item.get("page_number")
                if matched_concept and page_num in batch_pages:
                    paper.concept_mentions.append(
                        ConceptMention(
                            concept_name=matched_concept,
                            paper_title=paper.title,
                            page_number=int(page_num),
                            context_snippet=item.get("context_snippet", "").strip()
                        )
                    )

    def harmonize_master_bibliography(self, state: LiteratureBaseState) -> None:
        """BATCH PASS: Formats the entire bibliography simultaneously in 1 prompt."""
        papers = list(state.papers.values())
        if not papers:
            state.bibliography_en = "No sources available."
            return

        def get_sort_key(p: Paper) -> str:
            return p.authors[0].split()[-1].lower() if p.authors else p.title.lower()

        sorted_papers = sorted(papers, key=get_sort_key)
        metadata_list = [
            {
                "id": p.id,
                "title": p.title,
                "authors": p.authors,
                "year": p.year,
                "venue": p.venue,
                "doi_or_url": p.doi_or_url
            }
            for p in sorted_papers
        ]

        prompt = f"""
Target Citation Format: {state.citation_format}
Selected Papers Metadata:
{json.dumps(metadata_list, indent=2)}

Task:
Format this master reference list strictly in {state.citation_format}.
Requirements:
1. Apply 100% consistent typography and capitalization for archives (e.g. 'arXiv:XXXX.XXXXX').
2. Ensure alphabetical ordering.
3. Return strict JSON:
{{
  "citations": [
    {{"id": "paper_id", "formatted_string": "1. Author, A. (Year)..."}}
  ],
  "master_bibliography_text": "Complete formatted bibliography text"
}}
"""
        res = self.llm.generate_json(prompt, "Master bibliographic compiler. Return valid JSON.")
        state.bibliography_en = res.get("master_bibliography_text", "")
        for item in res.get("citations", []):
            p_id = item.get("id")
            if p_id in state.papers:
                state.papers[p_id].formatted_citation = item.get("formatted_string", "")

    def link_paper_network(self, state: LiteratureBaseState) -> None:
        papers = list(state.papers.values())
        if len(papers) < 2:
            return

        summaries = [{"title": p.title, "summary": p.summary_en, "concepts": p.extracted_concepts} for p in papers]
        prompt = f"""
Analyze these papers and identify conceptual cross-links:
{json.dumps(summaries, indent=2)}

Return strict JSON:
{{"relations": [{{"source_title": "Title A", "target_title": "Title B", "relation": "builds_upon"}}]}}
"""
        res = self.llm.generate_json(prompt, "Citation network analyzer.")
        for rel in res.get("relations", []):
            src = next((p for p in papers if p.title.lower() == rel.get("source_title", "").lower()), None)
            tgt = next((p for p in papers if p.title.lower() == rel.get("target_title", "").lower()), None)
            if src and tgt and src.id != tgt.id:
                if tgt.title not in src.related_paper_titles:
                    src.related_paper_titles.append(tgt.title)
                state.edges.append(GraphEdge(source_title=src.title, target_title=tgt.title, relation_type=rel.get("relation", "relates_to")))

    def build_overall_synthesis(self, state: LiteratureBaseState) -> None:
        papers = list(state.papers.values())
        if not papers:
            state.overall_summary_en = "No verified literature found."
            return

        summaries = [f"- **{p.title}** ({p.year}): {p.summary_en}" for p in papers]
        prompt = f"""
Topic: {state.topic}
Requirements: {state.requirements}

Synthesize these {len(papers)} accepted academic papers into a master literature review in English:
{chr(10).join(summaries)}

Structure:
1. Executive Summary & Research Consensus
2. Methodological Landscapes & Divergence
3. Research Gaps & Strategic Outlook
"""
        state.overall_summary_en = self.llm.generate(prompt, "Academic literature review author. Write strictly in English.")