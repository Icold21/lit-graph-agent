"""Centralized prompt templates.

Prompt engineering, abstract-level criteria filtering and synthesis wording
live here so the LLM-facing behaviour can be reviewed and tuned in one place.
"""

from typing import Any, Dict, Iterable, List

SYSTEM_LIBRARIAN = "Expert research librarian. Output only JSON."
SYSTEM_REVIEWER = "Scientific reviewer. Output only valid JSON."
SYSTEM_SYNTHESIZER = "Academic literature synthesizer. Output only valid JSON."
SYSTEM_ENCYCLOPEDIST = "Academic encyclopedist. Return only valid JSON."
SYSTEM_INDEXER = "Accurate concept indexer. Strict JSON."
SYSTEM_BIBLIOGRAPHER = "Master bibliographic compiler. Return valid JSON."
SYSTEM_NETWORK = "Citation network analyzer."
SYSTEM_REVIEW_AUTHOR = "Academic literature review author. Write strictly in English."


def sub_queries_prompt(topic: str, requirements: str, existing_queries: Iterable[str]) -> str:
    return f"""
Topic: {topic}
Requirements: {requirements}
Used: {list(existing_queries)}

Generate 2 distinct academic search queries in JSON:
{{"queries": ["query 1", "query 2"]}}
"""


def engine_selection_prompt(
    task: str,
    requirements: str,
    catalog: str,
    context: str = "",
) -> str:
    context_block = f"\nConversation / base context: {context}\n" if context else ""
    return f"""
You are routing an academic literature retrieval task to the most suitable search engines.

Research task: {task}
Requirements: {requirements}
{context_block}
Available search engines:
{catalog}

Choose engines based on their DESCRIPTIONS and the task itself:
- Match the topic's domain, recency needs, required metadata and expected source type.
- `primary` engines are queried first; `fallback` engines are used only if the primary returns too few results.
- Prefer ONE primary engine. Use two only when the task genuinely spans different source types.
- Do NOT pick the open web for rigorous peer-reviewed literature unless the task asks for gray literature, industry reports, documentation or news.
- Do NOT pick a source whose limitations contradict the task (e.g. arXiv for clinical medicine).
- Never invent engine names; use only the keys listed above.

Return strict JSON:
{{
  "primary": ["engine_key"],
  "fallback": ["engine_key"],
  "rationale": "One or two sentences explaining why this engine set fits the task",
  "confidence": 0.0
}}
"""


def validation_prompt(topic: str, requirements: str, title: str, year: Any, venue: Any, abstract: str) -> str:
    return f"""
Topic: {topic}
Requirements: {requirements}

Paper to Evaluate:
Title: {title}
Year: {year or 'Unknown'}
Venue: {venue or 'Unknown'}
Abstract: {abstract[:700]}

Evaluate strictly in JSON format:
{{
  "is_relevant": true,
  "meets_requirements": true,
  "topic_score": 8.5,
  "reason": "Concise 1-sentence explanation in English"
}}
"""


def paper_synthesis_prompt(title: str, authors: List[str], year: Any, venue: Any, abstract: str) -> str:
    return f"""
Synthesize the following paper strictly in English:
Title: {title}
Authors: {', '.join(authors)}
Year: {year}
Venue: {venue}
Abstract: {abstract[:6000]}

Concept extraction rules:
- Return 6-8 key scientific concepts that are explicitly mentioned in the abstract.
- Prefer specific methods, tasks, metrics, materials, datasets and technical terms.
- Prefer canonical multi-word names over bare acronyms.
- Avoid generic words such as system, approach, method, algorithm or result.
- Return each concept once.

Return strict JSON with concepts first:
{{
  "extracted_concepts": ["Specific concept 1", "Specific concept 2", "Specific concept 3"],
  "summary_en": "Deep single-paragraph executive summary in English",
  "key_findings_en": ["Key finding 1", "Key finding 2", "Key finding 3"],
  "methodology_en": "Methodology summary in English",
  "limitations_en": "Limitations identified in English"
}}
"""


def concept_definitions_prompt(topic: str, concept_names: List[str], paper_context: List[Dict[str, Any]]) -> str:
    import json

    return f"""
Domain Topic: "{topic}"
Target Concepts to define: {concept_names}

Referenced Sources Context:
{json.dumps(paper_context, indent=2, ensure_ascii=False)}

Task:
For EACH concept in the list, write a concise 2-sentence authoritative definition explaining its core role and consensus.
Return strict JSON mapping concept names to definitions:
{{
  "definitions": {{
    "Concept Name": "2-sentence authoritative definition and context..."
  }}
}}
"""


def concept_grounding_prompt(
    title: str,
    concepts: List[str],
    abstract: str,
    running_summary: str,
    batch_pages: List[int],
    batch_payload: Dict[int, str],
) -> str:
    import json

    return f"""
Paper Title: "{title}"
Target Concepts: {concepts}

[Context Anchor]: "{abstract[:200]}"
[Running Context]: "{running_summary}"
[Pages {batch_pages[0]}-{batch_pages[-1]}]:
{json.dumps(batch_payload, indent=2, ensure_ascii=False)}

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


def bibliography_prompt(citation_format: str, metadata_list: List[Dict[str, Any]]) -> str:
    import json

    return f"""
Target Citation Format: {citation_format}
Selected Papers Metadata:
{json.dumps(metadata_list, indent=2, ensure_ascii=False)}

Task:
Format every reference strictly in {citation_format}.
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


def relations_prompt(summaries: List[Dict[str, Any]]) -> str:
    import json

    return f"""
Analyze these papers and identify conceptual cross-links:
{json.dumps(summaries, indent=2, ensure_ascii=False)}

Return strict JSON:
{{"relations": [{{"source_title": "Title A", "target_title": "Title B", "relation": "builds_upon"}}]}}
"""


def review_prompt(topic: str, requirements: str, summaries: List[str], label: str = "master literature review") -> str:
    return f"""
Topic: {topic}
Requirements: {requirements}

Synthesize these {len(summaries)} accepted academic papers into a {label} in English:
{chr(10).join(summaries)}

Structure:
1. Executive Summary & Research Consensus
2. Methodological Landscapes & Divergence
3. Research Gaps & Strategic Outlook
"""


def merge_reviews_prompt(topic: str, requirements: str, joined_reviews: str) -> str:
    return f"""
Topic: {topic}
Requirements: {requirements}

Merge these partial literature reviews into one coherent master review in English:
{joined_reviews}

Structure:
1. Executive Summary & Research Consensus
2. Methodological Landscapes & Divergence
3. Research Gaps & Strategic Outlook
"""
