"""LLM Engineer agent: prompting, criteria filtering and synthesis."""

from typing import Any, List, Tuple

from ..llm.base import BaseLLMProvider
from ..llm.prompts import SYSTEM_LIBRARIAN, sub_queries_prompt
from ..utils.logging_setup import get_logger
from .bus import AgentBus, BaseTeamAgent
from .roles import TEAM_ROLES
from .synthesizer import LiteratureSynthesizer
from .validator import LiteratureValidator

logger = get_logger(__name__)


class PromptAgent(BaseTeamAgent):
    """Owns every LLM-facing decision: relevance, summaries, concepts, citations."""

    role = TEAM_ROLES["llm"]

    def __init__(self, llm: BaseLLMProvider, bus: AgentBus | None = None):
        super().__init__(bus)
        self.llm = llm
        self.validator = LiteratureValidator(llm)
        self.synthesizer = LiteratureSynthesizer(llm)

    def actions(self) -> Tuple[str, ...]:
        return (
            "generate_sub_queries",
            "validate",
            "synthesize_paper",
            "define_concepts",
            "ground_concepts",
            "bibliography",
            "link_network",
            "overview",
        )

    def _handle(self, action: str, **payload: Any) -> Any:
        if action == "generate_sub_queries":
            return self._generate_sub_queries(
                topic=payload["topic"],
                requirements=payload["requirements"],
                existing_queries=list(payload.get("existing_queries") or []),
            )
        if action == "validate":
            return self.validator.validate_candidate(
                paper=payload["paper"],
                topic=payload["topic"],
                requirements=payload["requirements"],
            )
        if action == "synthesize_paper":
            self.synthesizer.synthesize_paper_content(payload["paper"])
            return True
        if action == "define_concepts":
            self.synthesizer.synthesize_all_concept_hubs_batch(payload["state"])
            return len(payload["state"].concepts)
        if action == "ground_concepts":
            self.synthesizer.ground_concepts_to_pages(payload["paper"], payload["pages"])
            return len(payload["paper"].concept_mentions)
        if action == "bibliography":
            self.synthesizer.harmonize_master_bibliography(payload["state"])
            return len(payload["state"].papers)
        if action == "link_network":
            self.synthesizer.link_paper_network(payload["state"])
            return len(payload["state"].edges)
        if action == "overview":
            self.synthesizer.build_overall_synthesis(payload["state"])
            return len(payload["state"].overall_summary_en)
        raise ValueError(f"Unsupported prompt action: {action}")

    def _generate_sub_queries(
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


__all__ = ["PromptAgent"]
