"""Data / IR Engineer agent: academic APIs, search ranking and PDF retrieval."""

from typing import Any, Dict, Tuple

from ..search.engine import AcademicSearchEngine
from ..search.pdf_extractor import EphemeralPDFReader
from ..utils.logging_setup import get_logger
from .bus import AgentBus, BaseTeamAgent
from .roles import TEAM_ROLES

logger = get_logger(__name__)


class RetrievalAgent(BaseTeamAgent):
    """Talks to arXiv / Semantic Scholar / web fallback and streams PDFs."""

    role = TEAM_ROLES["retrieval"]

    def __init__(self, search_engine: AcademicSearchEngine, bus: AgentBus | None = None):
        super().__init__(bus)
        self.search_engine = search_engine
        self.pdf_reader = EphemeralPDFReader()

    def actions(self) -> Tuple[str, ...]:
        return ("search", "expand_citations", "fetch_pages", "suggest_queries")

    def _handle(self, action: str, **payload: Any) -> Any:
        if action == "search":
            return self.search_engine.search_and_rank(
                payload["query"], top_k=int(payload.get("top_k", 25))
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

