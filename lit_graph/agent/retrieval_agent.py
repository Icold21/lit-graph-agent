"""Data / IR Engineer agent: academic APIs, search ranking and PDF retrieval."""

from typing import Any, Dict, List, Tuple

from ..config import settings
from ..search.engine import AcademicSearchEngine
from ..search.pdf_extractor import EphemeralPDFReader
from ..search.router import SearchRouter
from ..search.tools import SEARCH_TOOLS
from ..utils.logging_setup import get_logger
from .bus import AgentBus, BaseTeamAgent
from .roles import TEAM_ROLES

logger = get_logger(__name__)


class RetrievalAgent(BaseTeamAgent):
    """Talks to arXiv / Semantic Scholar / web fallback and streams PDFs.

    Before searching, the agent asks the LLM engineer to pick the engines that
    fit the task description.  The resulting plan is normalised and validated
    here, then executed with an explicit fallback set.
    """

    role = TEAM_ROLES["retrieval"]

    def __init__(self, search_engine: AcademicSearchEngine, bus: AgentBus | None = None):
        super().__init__(bus)
        self.search_engine = search_engine
        self.pdf_reader = EphemeralPDFReader()
        available = getattr(search_engine, "available_engines", None)
        engines = available() if callable(available) else None
        self.router = SearchRouter(
            available=engines,
            max_primary=settings.search_router_max_primary,
        )

    def actions(self) -> Tuple[str, ...]:
        return (
            "plan_search",
            "describe_engines",
            "search",
            "expand_citations",
            "fetch_pages",
            "suggest_queries",
        )

    def _handle(self, action: str, **payload: Any) -> Any:
        if action == "plan_search":
            return self.plan_search(
                task=payload["task"],
                requirements=payload.get("requirements", ""),
                context=payload.get("context", ""),
            )
        if action == "describe_engines":
            return [tool.to_dict() for tool in self.router.catalog()]
        if action == "search":
            return self.search_engine.search_and_rank(
                payload["query"],
                top_k=int(payload.get("top_k", 25)),
                engines=payload.get("engines"),
                fallback_engines=payload.get("fallback_engines"),
                min_results=int(
                    payload.get("min_results", settings.search_fallback_min_results)
                ),
            )
        if action == "expand_citations":
            return self.search_engine.expand_citations(
                payload["paper_id"], limit=int(payload.get("limit", 3))
            )
        if action == "fetch_pages":
            return self.pdf_reader.fetch_pages(
                payload.get("doi_or_url") or "",
                max_pages=int(payload.get("max_pages", 15)),
                pdf_url=payload.get("pdf_url"),
            )
        if action == "suggest_queries":
            # Inter-agent hand-off: retrieval asks the LLM engineer to phrase
            # the next search round, then normalizes the result.
            return self.request(
                "llm",
                "generate_sub_queries",
                topic=payload["topic"],
                requirements=payload["requirements"],
                existing_queries=list(payload.get("existing_queries") or []),
            )
        raise ValueError(f"Unsupported retrieval action: {action}")

    def plan_search(self, task: str, requirements: str = "", context: str = "") -> Dict[str, Any]:
        """Choose search engines from their descriptions + the task via the LLM agent."""
        override = self._parse_override(settings.search_engines_override)
        if override:
            plan = self.router.manual_plan(override)
            logger.info("Manual search engines selected: %s", plan.describe())
            return plan.to_dict()

        if not settings.search_router_enabled:
            plan = self.router.heuristic_plan(
                task,
                requirements,
                reason="Dynamic engine routing is disabled; heuristic plan used.",
            )
            return plan.to_dict()

        decision: Any = None
        try:
            decision = self.request(
                "llm",
                "select_search_engines",
                task=task,
                requirements=requirements,
                catalog=self.router.catalog_prompt(),
                context=context,
            )
        except Exception as exc:  # noqa: BLE001 - routing must never break a run
            logger.warning("LLM engine selection failed, using heuristic plan: %s", exc)

        plan = self.router.build_plan(
            decision,
            task=task,
            requirements=requirements,
            source="llm" if decision else "heuristic",
        )
        logger.info("Search engine plan: %s | %s", plan.describe(), plan.rationale)
        return plan.to_dict()

    @staticmethod
    def _parse_override(value: str) -> List[str]:
        return [part.strip() for part in (value or "").split(",") if part.strip()]

    @staticmethod
    def merge_metadata(existing: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
        """Public helper used by the search engine and tests."""
        for field in ("citation_count", "influential_citation_count"):
            existing[field] = max(existing.get(field) or 0, incoming.get(field) or 0)
        for field in ("abstract", "pdf_url", "year", "doi_or_url", "venue"):
            if not existing.get(field) and incoming.get(field):
                existing[field] = incoming[field]
        return existing


__all__ = ["RetrievalAgent", "SEARCH_TOOLS"]
