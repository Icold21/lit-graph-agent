from typing import Any, Dict, List
import arxiv


class ArxivClient:
    """Search client for arXiv API."""

    def search(self, query: str, max_results: int = 15) -> List[Dict[str, Any]]:
        results = []
        try:
            client = arxiv.Client()
            search_query = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance
            )
            for r in client.results(search_query):
                results.append({
                    "id": f"arxiv_{r.get_short_id()}",
                    "title": r.title.replace("\n", " ").strip(),
                    "authors": [a.name for a in r.authors],
                    "year": r.published.year if r.published else None,
                    "venue": "arXiv",
                    "doi_or_url": r.entry_id,
                    "abstract": r.summary.replace("\n", " ").strip(),
                    "citation_count": 0,
                    "influential_citation_count": 0
                })
        except Exception as e:
            print(f"[ArxivClient] Warning: {e}")
        return results