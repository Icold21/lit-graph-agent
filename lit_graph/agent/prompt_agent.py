"""LLM Engineer agent: prompting, criteria filtering and synthesis.

Every LLM-facing operation lives here; the LangGraph workflow only routes data
into these methods and stores the resulting literature base back into state.
"""

from typing import Any, Dict, List

from ..llm.base import BaseLLMProvider
from ..llm.prompts import SYSTEM_LIBRARIAN, engine_selection_prompt, sub_queries_prompt
from ..models import LiteratureBaseState, Paper
from ..utils.logging_setup import get_logger
from .roles import TEAM_ROLES
from .synthesizer import LiteratureSynthesizer
from .validator import LiteratureValidator

logger = get_logger(__name__)


class PromptAgent:
    """Owns every LLM-facing decision: relevance, summaries, concepts, citations."""

    role = TEAM_ROLES["llm"]

    def __init__(self, llm: BaseLLMProvider):
        self.llm = llm
        self.validator = LiteratureValidator(llm)
        self.synthesizer = LiteratureSynthesizer(llm)

    # ------------------------------------------------------------ engine choice
    def choose_engines(
        self,
        task: str,
        requirements: str,
        catalog: str,
        context: str = "",
    ) -> Any:
        """Ask the model which retrieval backends match the task description."""
        prompt = engine_selection_prompt(task, requirements, catalog, context)
        try:
            return self.llm.generate_json(prompt, SYSTEM_LIBRARIAN)
        except Exception as exc:  # noqa: BLE001 - routing must never break a run
            logger.warning("Engine selection failed, falling back to heuristics: %s", exc)
            return {}

    def generate_sub_queries(
        self, topic: str, requirements: str, existing_queries: List[str]
    ) -> List[str]:
        prompt = sub_queries_prompt(topic, requirements, existing_queries)
        res = self.llm.generate_json(prompt, SYSTEM_LIBRARIAN)

        raw_queries: List[str] = []
        if isinstance(res, list):
            raw_queries = [str(item) for item in res if isinstance(item, (str, int, float))]
        elif isinstance(res, dict):
            candidate = res.get("queries", [])
            if isinstance(candidate, list):
                raw_queries = [str(item) for item in candidate if isinstance(item, (str, int, float))]
            else:
                logger.warning("Sub-query generator returned a non-list value: %r", candidate)

        seen = {query.strip().lower() for query in existing_queries}
        unique: List[str] = []
        for query in raw_queries:
            cleaned = query.strip()
            if cleaned and cleaned.lower() not in seen:
                seen.add(cleaned.lower())
                unique.append(cleaned)
        return unique[:2]

    # ---------------------------------------------------------------- validation
    def validate_candidate(self, paper: Paper, topic: str, requirements: str) -> bool:
        return self.validator.validate_candidate(paper=paper, topic=topic, requirements=requirements)

    # ----------------------------------------------------------------- synthesis
    def synthesize_paper(self, paper: Paper) -> bool:
        self.synthesizer.synthesize_paper_content(paper)
        return True

    def define_concepts(self, state: LiteratureBaseState) -> int:
        self.synthesizer.synthesize_all_concept_hubs_batch(state)
        return len(state.concepts)

    def ground_concepts(self, paper: Paper, pages: Dict[int, str]) -> int:
        self.synthesizer.ground_concepts_to_pages(paper, pages)
        return len(paper.concept_mentions)

    def build_bibliography(self, state: LiteratureBaseState) -> int:
        self.synthesizer.harmonize_master_bibliography(state)
        return len(state.papers)

    def link_network(self, state: LiteratureBaseState) -> int:
        self.synthesizer.link_paper_network(state)
        return len(state.edges)

    def build_overview(self, state: LiteratureBaseState) -> int:
        self.synthesizer.build_overall_synthesis(state)
        return len(state.overall_summary_en)


__all__ = ["PromptAgent"]
