from typing import Any, Dict, List, Optional
import requests


class SemanticScholarClient:
    """Client for Semantic Scholar Graph API with citations & references."""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.headers = {"x-api-key": api_key} if api_key else {}

    def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        results = []
        url = f"{self.BASE_URL}/paper/search"
        params = {
            "query": query,
            "limit": limit,
            "fields": "paperId,title,authors,year,venue,abstract,url,citationCount,influentialCitationCount"
        }
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=12)
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                for item in data:
                    results.append({
                        "id": f"s2_{item.get('paperId')}",
                        "title": item.get("title", "Untitled").strip(),
                        "authors": [a["name"] for a in item.get("authors", [])],
                        "year": item.get("year"),
                        "venue": item.get("venue") or "Semantic Scholar",
                        "doi_or_url": item.get("url"),
                        "abstract": item.get("abstract") or "",
                        "citation_count": item.get("citationCount") or 0,
                        "influential_citation_count": item.get("influentialCitationCount") or 0
                    })
        except Exception as e:
            print(f"[SemanticScholarClient] Warning: {e}")
        return results

    def get_citations_and_references(self, paper_id: str, limit: int = 5) -> Dict[str, List[str]]:
        clean_id = paper_id.replace("s2_", "").replace("arxiv_", "")
        url = f"{self.BASE_URL}/paper/{clean_id}"
        params = {
            "fields": "references.title,references.citationCount,citations.title,citations.citationCount"
        }
        ref_titles = []
        cit_titles = []

        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                refs = sorted(data.get("references", []), key=lambda x: x.get("citationCount") or 0, reverse=True)
                cits = sorted(data.get("citations", []), key=lambda x: x.get("citationCount") or 0, reverse=True)
                
                ref_titles = [r["title"].strip() for r in refs if r.get("title")][:limit]
                cit_titles = [c["title"].strip() for c in cits if c.get("title")][:limit]
        except Exception:
            pass

        return {"references": ref_titles, "citations": cit_titles}