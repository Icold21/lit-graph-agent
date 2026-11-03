import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from ..utils.cache import get_cache
from ..utils.logging_setup import get_logger
from .arxiv_client import ArxivClient
from .s2_client import SemanticScholarClient
from .tools import DEFAULT_TOOL_ORDER, SEARCH_TOOLS
from .web_scraper import WebScraperClient

logger = get_logger(__name__)

CACHE_NAMESPACE = "academic_search_v3"


class AcademicSearchEngine:
    """Aggregates searches, calculates popularity heuristics, and expands citation networks.

    The engine set is no longer hard-coded: callers may pass the engines chosen
    by the LLM (see ``lit_graph.search.router``), with an explicit fallback set
    that is queried only when the primary engines return too few candidates.
    """

    def __init__(self, s2_api_key: str | None = None):
        self.arxiv = ArxivClient()
        self.s2 = SemanticScholarClient(s2_api_key)
        self.web = WebScraperClient()
        self._clients = {
            "semantic_scholar": self.s2,
            "arxiv": self.arxiv,
            "web": self.web,
        }
        self._cache = get_cache()

    def available_engines(self) -> List[str]:
        return [key for key in DEFAULT_TOOL_ORDER if key in self._clients]

    def _calculate_pre_rank_heuristic(self, item: Dict[str, Any], query: str) -> float:
        citations = item.get("citation_count") or 0
        influential = item.get("influential_citation_count") or 0
        year = item.get("year")
        title = (item.get("title") or "").lower()
        abstract = (item.get("abstract") or "").lower()
        current_year = datetime.now().year

        # Logarithmic popularity
        popularity = math.log1p(citations) + (1.5 * math.log1p(influential))

        # Freshness / Recency
        recency = 1.0
        if year:
            age = max(0, current_year - year)
            recency = max(0.2, 1.0 - (age * 0.05))

        # Lexical keyword match
        words = [w.lower() for w in query.split() if len(w) > 2]
        matches = sum(2.0 for w in words if w in title) + sum(0.5 for w in words if w in abstract)

        return (popularity * 0.45) + (recency * 2.0) + (matches * 1.5)

    @staticmethod
    def _merge_candidate(existing: Dict[str, Any], incoming: Dict[str, Any]) -> None:
        """Keep the richest metadata when the same paper arrives from two sources."""
        for field in ("citation_count", "influential_citation_count"):
            existing[field] = max(existing.get(field) or 0, incoming.get(field) or 0)

        # Prefer the record that actually has an abstract / PDF / year.
        for field, validator in (
            ("abstract", lambda value: bool(value)),
            ("pdf_url", lambda value: bool(value)),
            ("year", lambda value: value is not None),
            ("doi_or_url", lambda value: bool(value)),
            ("venue", lambda value: bool(value) and value != "Semantic Scholar"),
        ):
            if not validator(existing.get(field)) and validator(incoming.get(field)):
                existing[field] = incoming[field]

    def _query_engine(self, engine: str, query: str, limit: int) -> List[Dict[str, Any]]:
        client = self._clients.get(engine)
        if client is None:
            logger.warning("Unknown search engine %r, skipping", engine)
            return []

        try:
            if engine == "arxiv":
                results = client.search(query, max_results=limit)
            elif engine == "web":
                results = client.search(query, max_results=min(limit, 5))
            else:
                results = client.search(query, limit=limit)
        except Exception as exc:  # noqa: BLE001 - one engine must not break the search
            logger.warning("Search engine %r failed for %r: %s", engine, query, exc)
            return []

        for paper in results:
            paper.setdefault("source_engine", engine)
        return results

    @staticmethod
    def _normalize_engines(engines: Optional[Sequence[str]]) -> List[str]:
        if not engines:
            return []
        return [key for key in dict.fromkeys(engines) if key in SEARCH_TOOLS]

    def search_and_rank(
        self,
        query: str,
        top_k: int = 25,
        engines: Optional[Sequence[str]] = None,
        fallback_engines: Optional[Sequence[str]] = None,
        min_results: int = 5,
    ) -> List[Dict[str, Any]]:
        if not query.strip():
            return []

        primary = self._normalize_engines(engines)
        fallback = self._normalize_engines(fallback_engines)
        if engines is None:
            # Backwards-compatible default: both scholarly indexes first, web
            # only as a fallback when the result set is thin.
            primary = ["semantic_scholar", "arxiv"]
            fallback = ["web"]
        if not primary:
            primary = list(DEFAULT_TOOL_ORDER)

        cache_key = {
            "query": query.strip(),
            "top_k": top_k,
            "primary": primary,
            "fallback": fallback,
            "min_results": min_results,
        }
        cached = self._cache.get(CACHE_NAMESPACE, cache_key)
        if isinstance(cached, list):
            logger.debug("Cache hit for search query %r", query)
            return cached

        candidates: List[Dict[str, Any]] = []
        for engine in primary:
            candidates.extend(self._query_engine(engine, query, top_k))

        used = set(primary)
        if len(candidates) < min_results:
            for engine in fallback:
                if engine in used:
                    continue
                logger.info(
                    "Primary engines %s returned %s results; falling back to %s",
                    primary,
                    len(candidates),
                    engine,
                )
                candidates.extend(self._query_engine(engine, query, top_k))
                used.add(engine)
                if len(candidates) >= min_results:
                    break

        # Deduplication with metadata merging
        unique_map: Dict[str, Dict[str, Any]] = {}
        for paper in candidates:
            title = paper.get("title") or ""
            norm_title = "".join(filter(str.isalnum, title.lower()))
            if not norm_title:
                continue
            existing = unique_map.get(norm_title)
            if existing is None:
                unique_map[norm_title] = paper
            else:
                self._merge_candidate(existing, paper)

        for paper in unique_map.values():
            paper["heuristic_score"] = self._calculate_pre_rank_heuristic(paper, query)

        ranked = sorted(unique_map.values(), key=lambda p: p["heuristic_score"], reverse=True)[:top_k]
        self._cache.set(CACHE_NAMESPACE, cache_key, ranked)
        return ranked

    def expand_citations(self, paper_id: str, limit: int = 3) -> Dict[str, List[str]]:
        if not paper_id or paper_id.startswith("web_"):
            return {"references": [], "citations": []}

        cache_key = {"paper_id": paper_id, "limit": limit}
        cached = self._cache.get(f"{CACHE_NAMESPACE}_citations", cache_key)
        if isinstance(cached, dict):
            return cached

        result = self.s2.get_citations_and_references(paper_id, limit=limit)
        self._cache.set(f"{CACHE_NAMESPACE}_citations", cache_key, result)
        return result
