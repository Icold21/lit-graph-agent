from typing import Any, Dict, List, Optional

from ..utils.http import request_with_retry
from ..utils.logging_setup import get_logger

logger = get_logger(__name__)


class SemanticScholarClient:
    """Client for Semantic Scholar Graph API with citations & references."""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    SEARCH_FIELDS = (
        "paperId,title,authors,year,venue,abstract,url,citationCount,"
        "influentialCitationCount,openAccessPdf,externalIds"
    )

    def __init__(self, api_key: Optional[str] = None):
        self.headers = {"x-api-key": api_key} if api_key else {}

    @staticmethod
    def to_api_id(paper_id: str) -> Optional[str]:
        """Translate an internal paper id into a Semantic Scholar API id.

        arXiv ids must keep their ``ARXIV:`` prefix; bare ids are treated as
        S2 hashes. Web-scraped sources have no S2 representation.
        """
        if not paper_id:
            return None
        if paper_id.startswith("s2_"):
            return paper_id[3:]
        if paper_id.startswith("arxiv_"):
            return f"ARXIV:{paper_id[6:]}"
        if paper_id.startswith("web_"):
            return None
        return paper_id

    def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        if not query.strip():
            return results

        url = f"{self.BASE_URL}/paper/search"
        params = {"query": query, "limit": max(1, min(limit, 100)), "fields": self.SEARCH_FIELDS}
        response = request_with_retry("GET", url, params=params, headers=self.headers)
        if response is None:
            logger.warning("Semantic Scholar search unavailable for query %r", query)
            return results
        if response.status_code != 200:
            logger.warning("Semantic Scholar search returned HTTP %s for %r", response.status_code, query)
            return results

        try:
            data = response.json().get("data", [])
        except ValueError:
            logger.warning("Semantic Scholar returned invalid JSON for query %r", query)
            return results

        for item in data:
            open_access = item.get("openAccessPdf") or {}
            external_ids = item.get("externalIds") or {}
            doi = external_ids.get("DOI")
            url_value = item.get("url") or (f"https://doi.org/{doi}" if doi else None)
            results.append(
                {
                    "id": f"s2_{item.get('paperId')}",
                    "title": (item.get("title") or "Untitled").strip(),
                    "authors": [author.get("name", "") for author in item.get("authors", []) if author.get("name")],
                    "year": item.get("year"),
                    "venue": item.get("venue") or "Semantic Scholar",
                    "doi_or_url": url_value,
                    "pdf_url": open_access.get("url"),
                    "abstract": item.get("abstract") or "",
                    "citation_count": item.get("citationCount") or 0,
                    "influential_citation_count": item.get("influentialCitationCount") or 0,
                }
            )
        return results

    def _fetch_relation_list(self, paper_id: str, kind: str, limit: int) -> List[str]:
        """Fetch references or citations, sorted by citation count."""
        api_id = self.to_api_id(paper_id)
        if not api_id:
            return []

        url = f"{self.BASE_URL}/paper/{api_id}/{kind}"
        params = {
            "limit": max(1, min(limit * 5, 100)),
            "fields": "title,citationCount",
        }
        response = request_with_retry("GET", url, params=params, headers=self.headers)
        if response is None or response.status_code != 200:
            status = "unavailable" if response is None else f"HTTP {response.status_code}"
            logger.info("Semantic Scholar %s lookup for %s failed (%s)", kind, paper_id, status)
            return []

        try:
            data = response.json().get("data", [])
        except ValueError:
            return []

        entries = []
        for entry in data:
            paper = entry.get("citedPaper") or entry.get("citingPaper") or entry
            title = (paper.get("title") or "").strip()
            if title:
                entries.append((title, paper.get("citationCount") or 0))
        entries.sort(key=lambda item: item[1], reverse=True)

        unique_titles: List[str] = []
        for title, _ in entries:
            if title not in unique_titles:
                unique_titles.append(title)
            if len(unique_titles) >= limit:
                break
        return unique_titles

    def get_citations_and_references(self, paper_id: str, limit: int = 5) -> Dict[str, List[str]]:
        return {
            "references": self._fetch_relation_list(paper_id, "references", limit),
            "citations": self._fetch_relation_list(paper_id, "citations", limit),
        }
