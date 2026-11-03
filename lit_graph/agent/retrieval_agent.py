"""Data / IR Engineer agent: academic APIs, search ranking and PDF retrieval.

The class is a pure service now: the LangGraph workflow decides *when* each
step runs, while this agent owns *how* retrieval works (engine catalog,
validated engine plans, search execution, citation expansion, PDF pages).
"""

from typing import Any, Dict, List, Sequence

from ..config import settings
from ..search.engine import AcademicSearchEngine
from ..search.pdf_extractor import EphemeralPDFReader
from ..search.router import SearchRouter
from ..utils.logging_setup import get_logger
from .roles import TEAM_ROLES

logger = get_logger(__name__)


class RetrievalAgent:
    """Talks to arXiv / Semantic Scholar / web fallback and streams PDFs."""

    role = TEAM_ROLES["retrieval"]

    def __init__(self, search_engine: AcademicSearchEngine):
        self.search_engine = search_engine
        self.pdf_reader = EphemeralPDFReader()
        available = getattr(search_engine, "available_engines", None)
        engines = available() if callable(available) else None
        self.router = SearchRouter(
            available=engines,
            max_primary=settings.search_router_max_primary,
        )

    # ------------------------------------------------------------ engine choice
    def catalog(self) -> List[Dict[str, Any]]:
        return [tool.to_dict() for tool in self.router.catalog()]

    def catalog_prompt(self) -> str:
        return self.router.catalog_prompt()

    def plan_request(self, task: str, requirements: str, context: str = "") -> Dict[str, Any]:
        """Describe how the plan should be produced (graph routing decision)."""
        override = self._parse_override(settings.search_engines_override)
        if override:
            return {"needs_llm": False, "source": "manual", "override": override}
        if not settings.search_router_enabled:
            return {"needs_llm": False, "source": "heuristic", "override": []}
        return {
            "needs_llm": True,
            "source": "llm",
            "override": [],
            "task": task,
            "requirements": requirements,
            "context": context,
        }

    def finalize_plan(
        self,
        decision: Any,
        *,
        task: str,
        requirements: str,
        source: str = "llm",
    ) -> Dict[str, Any]:
        """Validate the model's engine choice and fall back to heuristics if needed."""
        override = self._parse_override(settings.search_engines_override)
        if override:
            plan = self.router.manual_plan(override)
        elif not settings.search_router_enabled or source == "heuristic":
            plan = self.router.heuristic_plan(
                task,
                requirements,
                reason="Dynamic engine routing is disabled; heuristic plan used.",
            )
        else:
            plan = self.router.build_plan(
                decision,
                task=task,
                requirements=requirements,
                source="llm" if decision else "heuristic",
            )

        logger.info("Search engine plan: %s | %s", plan.describe(), plan.rationale)
        return plan.to_dict()

    # ------------------------------------------------------------------ retrieval
    def search(
        self,
        query: str,
        top_k: int = 25,
        engines: Sequence[str] | None = None,
        fallback_engines: Sequence[str] | None = None,
        min_results: int | None = None,
    ) -> List[Dict[str, Any]]:
        return self.search_engine.search_and_rank(
            query,
            top_k=top_k,
            engines=engines,
            fallback_engines=fallback_engines,
            min_results=int(
                min_results
                if min_results is not None
                else settings.search_fallback_min_results
            ),
        )

    def expand_citations(self, paper_id: str, limit: int = 3) -> Dict[str, List[str]]:
        return self.search_engine.expand_citations(paper_id, limit=limit)

    def fetch_pages(
        self,
        doi_or_url: str = "",
        max_pages: int = 15,
        pdf_url: str | None = None,
    ) -> Dict[int, str]:
        return self.pdf_reader.fetch_pages(doi_or_url, max_pages=max_pages, pdf_url=pdf_url)

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


__all__ = ["RetrievalAgent"]
