from typing import Any, Dict, List
import requests
from bs4 import BeautifulSoup


class WebScraperClient:
    """Lightweight web scraper fallback for academic and open literature search."""

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        results = []
        try:
            url = "https://html.duckduckgo.com/html/"
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.post(url, data={"q": f"{query} research paper pdf"}, headers=headers, timeout=8)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for r in soup.select(".result")[:max_results]:
                    title_elem = r.select_one(".result__title")
                    snippet_elem = r.select_one(".result__snippet")
                    url_elem = r.select_one(".result__url")
                    
                    if title_elem and snippet_elem:
                        results.append({
                            "id": f"web_{abs(hash(title_elem.get_text())) % 1000000}",
                            "title": title_elem.get_text().strip(),
                            "authors": ["Web Source"],
                            "year": None,
                            "venue": "Web Search",
                            "doi_or_url": url_elem.get_text().strip() if url_elem else "",
                            "abstract": snippet_elem.get_text().strip(),
                            "citation_count": 1,
                            "influential_citation_count": 0
                        })
        except Exception:
            pass
        return results