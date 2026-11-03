from typing import Any, Dict, List

import arxiv

from ..utils.logging_setup import get_logger

logger = get_logger(__name__)


class ArxivClient:
    """Search client for arXiv API."""

    def search(self, query: str, max_results: int = 15) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        if not query.strip():
            return results

        try:
            client = arxiv.Client()
            search_query = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance,
            )
            for record in client.results(search_query):
                results.append(
                    {
                        "id": f"arxiv_{record.get_short_id()}",
                        "title": record.title.replace("\n", " ").strip(),
                        "authors": [author.name for author in record.authors],
                        "year": record.published.year if record.published else None,
                        "venue": "arXiv",
                        "doi_or_url": record.entry_id,
                        "pdf_url": record.pdf_url,
                        "abstract": record.summary.replace("\n", " ").strip(),
                        "citation_count": 0,
                        "influential_citation_count": 0,
                    }
                )
        except Exception as exc:  # noqa: BLE001 - arxiv package raises various errors
            logger.warning("arXiv search failed for %r: %s", query, exc)
        return results
