import json
from typing import Any, Dict, Iterable, List

from ..config import settings
from ..llm.base import BaseLLMProvider
from ..models import ConceptMention, GraphEdge, LiteratureBaseState, Paper
from ..utils.logging_setup import get_logger

logger = get_logger(__name__)


def _chunks(items: List[Any], size: int) -> Iterable[List[Any]]:
    size = max(1, size)
    for index in range(0, len(items), size):
        yield items[index : index + size]


def _as_string_list(value: Any, limit: int | None = None) -> List[str]:
    if not isinstance(value, list):
        return []
    cleaned = [str(item).strip() for item in value if isinstance(item, (str, int, float)) and str(item).strip()]
    return cleaned[:limit] if limit else cleaned


class LiteratureSynthesizer:
    """Synthesizes paper notes, batch-defines concept hubs, and harmonizes bibliographies."""

    def __init__(self, llm: BaseLLMProvider):
        self.llm = llm

    # ------------------------------------------------------------------ papers
    def synthesize_paper_content(self, paper: Paper) -> None:
        """Extracts executive summary, methodology, and key concepts in 1 fast LLM call."""
        prompt = f"""
Synthesize the following paper strictly in English:
Title: {paper.title}
Authors: {', '.join(paper.authors)}
Year: {paper.year}
Venue: {paper.venue}
Abstract: {paper.abstract[:6000]}

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
        if not isinstance(res, dict):
            logger.warning("Paper synthesis returned %s for %r; keeping metadata only", type(res).__name__, paper.title)
            return

        paper.summary_en = str(res.get("summary_en") or "")
        paper.key_findings_en = _as_string_list(res.get("key_findings_en"))
        paper.methodology_en = str(res.get("methodology_en") or "")
        paper.limitations_en = str(res.get("limitations_en") or "")

        concepts = _as_string_list(res.get("extracted_concepts"))
        paper.extracted_concepts_all = concepts
        paper.extracted_concepts = concepts[: settings.max_concepts_per_paper]

    # ---------------------------------------------------------------- concepts
    def synthesize_all_concept_hubs_batch(self, state: LiteratureBaseState) -> None:
        """
        Generates encyclopedic definitions for concepts that do not have one yet.

        Concepts are processed in bounded batches so large knowledge bases never
        hit the model's output-token limit (which previously produced placeholder
        definitions for half of the hubs).
        """
        missing = [hub for hub in state.concepts.values() if not hub.summary_en.strip()]
        if not missing:
            return

        for batch in _chunks(missing, settings.concept_batch_size):
            concept_names = [hub.name for hub in batch]
            relevant_papers = [
                paper
                for paper in state.papers.values()
                if any(
                    concept_name.lower() in {concept.lower() for concept in paper.extracted_concepts}
                    for concept_name in concept_names
                )
            ]
            paper_context = [
                {
                    "title": paper.title,
                    "year": paper.year,
                    "summary": (paper.summary_en or paper.abstract)[:250],
                    "concepts": paper.extracted_concepts,
                }
                for paper in relevant_papers[:20]
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
            definitions: Dict[str, Any] = {}
            if isinstance(res, dict):
                candidate = res.get("definitions", res)
                if isinstance(candidate, dict):
                    definitions = candidate

            for hub in batch:
                definition = definitions.get(hub.name)
                if not definition:
                    lowered = hub.name.lower()
                    definition = next(
                        (value for key, value in definitions.items() if str(key).lower() == lowered),
                        "",
                    )
                if definition:
                    hub.summary_en = str(definition).strip()

        for hub in missing:
            if not hub.summary_en.strip():
                source_count = len(hub.mentions) or 1
                hub.summary_en = f"Key conceptual node referenced across {source_count} literature sources."
                logger.warning("Concept %r received a fallback definition", hub.name)

    def ground_concepts_to_pages(self, paper: Paper, pages_dict: Dict[int, str], batch_size: int = 3) -> None:
        """Deep scanning (Used only when --deep flag is enabled)."""
        if not pages_dict or not paper.extracted_concepts:
            return

        page_numbers = sorted(pages_dict.keys())
        target_concepts_lower = {concept.lower(): concept for concept in paper.extracted_concepts}
        running_summary = f"Abstract: {paper.abstract[:250]}..." if paper.abstract else "Beginning of manuscript."
        seen_mentions = {
            (mention.concept_name.lower(), mention.page_number) for mention in paper.concept_mentions
        }

        for index in range(0, len(page_numbers), batch_size):
            batch_pages = page_numbers[index : index + batch_size]
            batch_payload = {number: pages_dict[number][:5000] for number in batch_pages}

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
            if isinstance(res, dict) and res.get("updated_running_summary"):
                running_summary = str(res.get("updated_running_summary"))

            raw_mentions: Any = []
            if isinstance(res, list):
                raw_mentions = res
            elif isinstance(res, dict):
                raw_mentions = res.get("mentions", [])

            if not isinstance(raw_mentions, list):
                logger.warning("Concept grounding returned malformed mentions for %r", paper.title)
                continue

            for item in raw_mentions:
                if not isinstance(item, dict):
                    continue
                concept_raw = str(item.get("concept_name", "")).strip()
                matched_concept = target_concepts_lower.get(concept_raw.lower())
                page_number = item.get("page_number")
                if not matched_concept or page_number not in batch_pages:
                    continue
                mention_key = (matched_concept.lower(), page_number)
                if mention_key in seen_mentions:
                    continue
                seen_mentions.add(mention_key)
                paper.concept_mentions.append(
                    ConceptMention(
                        concept_name=matched_concept,
                        paper_title=paper.title,
                        page_number=int(page_number),
                        context_snippet=str(item.get("context_snippet", "")).strip(),
                    )
                )

    # ------------------------------------------------------------ bibliography
    @staticmethod
    def _sort_key(paper: Paper) -> str:
        return paper.authors[0].split()[-1].lower() if paper.authors else paper.title.lower()

    @staticmethod
    def _fallback_citation(paper: Paper, citation_format: str) -> str:
        authors = ", ".join(paper.authors) if paper.authors else "Unknown"
        year = paper.year or "n.d."
        venue = paper.venue or ""
        url = paper.doi_or_url or ""
        if "bibtex" in citation_format.lower():
            key = "".join(char for char in (paper.authors[0].split()[-1] if paper.authors else "ref") if char.isalnum())
            return (
                f"@article{{{key}{year},\n"
                f"  title = {{{paper.title}}},\n"
                f"  author = {{{' and '.join(paper.authors) or 'Unknown'}}},\n"
                f"  year = {{{year}}},\n"
                f"  journal = {{{venue}}},\n"
                f"  url = {{{url}}}\n"
                f"}}"
            )
        parts = [f"{authors} ({year}). {paper.title}."]
        if venue:
            parts.append(f"{venue}.")
        if url:
            parts.append(url)
        return " ".join(parts)

    def harmonize_master_bibliography(self, state: LiteratureBaseState) -> None:
        """BATCH PASS: formats the bibliography in bounded batches."""
        papers = sorted(state.papers.values(), key=self._sort_key)
        if not papers:
            state.bibliography_en = "No sources available."
            return

        for batch in _chunks(list(papers), settings.bibliography_batch_size):
            metadata_list = [
                {
                    "id": paper.id,
                    "title": paper.title,
                    "authors": paper.authors,
                    "year": paper.year,
                    "venue": paper.venue,
                    "doi_or_url": paper.doi_or_url,
                }
                for paper in batch
            ]

            prompt = f"""
Target Citation Format: {state.citation_format}
Selected Papers Metadata:
{json.dumps(metadata_list, indent=2, ensure_ascii=False)}

Task:
Format every reference strictly in {state.citation_format}.
Requirements:
1. Apply 100% consistent typography and capitalization for archives (e.g. 'arXiv:XXXX.XXXXX').
2. Return one entry per input paper.
3. Return strict JSON:
{{
  "citations": [
    {{"id": "paper_id", "formatted_string": "Author, A. (Year). Title..."}}
  ]
}}
"""
            res = self.llm.generate_json(prompt, "Master bibliographic compiler. Return valid JSON.")
            citations_list: Any = []
            if isinstance(res, dict):
                citations_list = res.get("citations", [])
            elif isinstance(res, list):
                citations_list = res

            if isinstance(citations_list, list):
                for item in citations_list:
                    if not isinstance(item, dict):
                        continue
                    paper_id = item.get("id")
                    if paper_id in state.papers and item.get("formatted_string"):
                        state.papers[paper_id].formatted_citation = str(item["formatted_string"]).strip()
            else:
                logger.warning("Bibliography batch returned malformed citations")

        missing = 0
        for paper in papers:
            if not paper.formatted_citation.strip():
                paper.formatted_citation = self._fallback_citation(paper, state.citation_format)
                missing += 1
        if missing:
            logger.warning("Used fallback formatting for %s bibliography entries", missing)

        state.bibliography_en = "\n\n".join(paper.formatted_citation for paper in papers)

    # ------------------------------------------------------------------ graph
    def link_paper_network(self, state: LiteratureBaseState) -> None:
        """Finds conceptual cross-links between papers defensively handling dict or list outputs."""
        papers = list(state.papers.values())
        if len(papers) < 2:
            return

        summaries = [
            {
                "title": paper.title,
                "summary": (paper.summary_en or paper.abstract)[:600],
                "concepts": paper.extracted_concepts,
            }
            for paper in papers
        ]
        prompt = f"""
Analyze these papers and identify conceptual cross-links:
{json.dumps(summaries, indent=2, ensure_ascii=False)}

Return strict JSON:
{{"relations": [{{"source_title": "Title A", "target_title": "Title B", "relation": "builds_upon"}}]}}
"""
        res = self.llm.generate_json(prompt, "Citation network analyzer.")

        # Defensive parsing: handles both {"relations": [...]} and [...]
        relations_list: Any = []
        if isinstance(res, list):
            relations_list = res
        elif isinstance(res, dict):
            relations_list = res.get("relations", [])

        if not isinstance(relations_list, list):
            logger.warning("Citation network returned malformed relations")
            return

        for relation in relations_list:
            if not isinstance(relation, dict):
                continue
            source_title = str(relation.get("source_title", ""))
            target_title = str(relation.get("target_title", ""))

            source = next((paper for paper in papers if paper.title.lower() == source_title.lower()), None)
            target = next((paper for paper in papers if paper.title.lower() == target_title.lower()), None)
            if source and target and source.id != target.id:
                if target.title not in source.related_paper_titles:
                    source.related_paper_titles.append(target.title)
                state.add_edge(
                    GraphEdge(
                        source_title=source.title,
                        target_title=target.title,
                        relation_type=str(relation.get("relation") or "relates_to"),
                    )
                )

    def build_overall_synthesis(self, state: LiteratureBaseState) -> None:
        papers = list(state.papers.values())
        if not papers:
            state.overall_summary_en = "No verified literature found."
            return

        summaries = [f"- **{paper.title}** ({paper.year}): {(paper.summary_en or paper.abstract)[:900]}" for paper in papers]
        batches = list(_chunks(summaries, 20))

        if len(batches) == 1:
            state.overall_summary_en = self._synthesize_review(state, batches[0])
            return

        partial_reviews = [
            self._synthesize_review(state, batch, partial=True) for batch in batches
        ]
        joined = "\n\n".join(f"### Partial review {index + 1}\n{text}" for index, text in enumerate(partial_reviews))
        prompt = f"""
Topic: {state.topic}
Requirements: {state.requirements}

Merge these partial literature reviews into one coherent master review in English:
{joined}

Structure:
1. Executive Summary & Research Consensus
2. Methodological Landscapes & Divergence
3. Research Gaps & Strategic Outlook
"""
        state.overall_summary_en = self.llm.generate(
            prompt, "Academic literature review author. Write strictly in English."
        )

    def _synthesize_review(self, state: LiteratureBaseState, summaries: List[str], partial: bool = False) -> str:
        label = "partial literature review" if partial else "master literature review"
        prompt = f"""
Topic: {state.topic}
Requirements: {state.requirements}

Synthesize these {len(summaries)} accepted academic papers into a {label} in English:
{chr(10).join(summaries)}

Structure:
1. Executive Summary & Research Consensus
2. Methodological Landscapes & Divergence
3. Research Gaps & Strategic Outlook
"""
        return self.llm.generate(prompt, "Academic literature review author. Write strictly in English.")
