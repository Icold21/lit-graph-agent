import math
from datetime import datetime
from typing import Any, Dict, List
from .arxiv_client import ArxivClient
from .s2_client import SemanticScholarClient
from .web_scraper import WebScraperClient


class AcademicSearchEngine:
    """Aggregates searches, calculates popularity heuristics, and expands citation networks."""

    def __init__(self, s2_api_key: str | None = None):
        self.arxiv = ArxivClient()
        self.s2 = SemanticScholarClient(s2_api_key)
        self.web = WebScraperClient()

    def _calculate_pre_rank_heuristic(self, item: Dict[str, Any], query: str) -> float:
        citations = item.get("citation_count", 0)
        influential = item.get("influential_citation_count", 0)
        year = item.get("year")
        title = item.get("title", "").lower()
        abstract = item.get("abstract", "").lower()
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

    def search_and_rank(self, query: str, top_k: int = 25) -> List[Dict[str, Any]]:
        candidates = []
        candidates.extend(self.s2.search(query, limit=top_k))
        candidates.extend(self.arxiv.search(query, max_results=top_k))
        if len(candidates) < 5:
            candidates.extend(self.web.search(query, max_results=5))

        # Deduplication
        unique_map = {}
        for paper in candidates:
            norm_title = "".join(filter(str.isalnum, paper["title"].lower()))
            if norm_title and norm_title not in unique_map:
                paper["heuristic_score"] = self._calculate_pre_rank_heuristic(paper, query)
                unique_map[norm_title] = paper

        ranked = sorted(unique_map.values(), key=lambda p: p["heuristic_score"], reverse=True)
        return ranked[:top_k]

    def expand_citations(self, paper_id: str, limit: int = 3) -> Dict[str, List[str]]:
        return self.s2.get_citations_and_references(paper_id, limit=limit)