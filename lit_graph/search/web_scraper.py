import hashlib
from typing import Any, Dict, List
from urllib.parse import parse_qs, unquote, urlparse

from bs4 import BeautifulSoup

from ..utils.http import request_with_retry
from ..utils.logging_setup import get_logger

logger = get_logger(__name__)


class WebScraperClient:
    """Lightweight web scraper fallback for academic and open literature search."""

    @staticmethod
    def _stable_id(title: str) -> str:
        digest = hashlib.sha1(title.encode("utf-8")).hexdigest()[:10]
        return f"web_{digest}"

    @staticmethod
    def _resolve_url(raw_url: str) -> str:
        """DuckDuckGo wraps results in a redirect; unwrap it when possible."""
        if not raw_url:
            return ""
        if raw_url.startswith("//"):
            raw_url = f"https:{raw_url}"
        parsed = urlparse(raw_url)
        if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
            target = parse_qs(parsed.query).get("uddg")
            if target:
                return unquote(target[0])
        return raw_url

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        if not query.strip():
            return results

        try:
            url = "https://html.duckduckgo.com/html/"
            headers = {"User-Agent": "Mozilla/5.0 (compatible; LitGraphAgent/1.0)"}
            response = request_with_retry(
                "POST",
                url,
                data={"q": f"{query} research paper pdf"},
                headers=headers,
            )
            if response is None or response.status_code != 200:
                return results

            soup = BeautifulSoup(response.text, "html.parser")
            for result in soup.select(".result")[:max_results]:
                title_elem = result.select_one(".result__title")
                snippet_elem = result.select_one(".result__snippet")
                url_elem = result.select_one(".result__url")
                link_elem = result.select_one(".result__a")
                if not title_elem or not snippet_elem:
                    continue

                title = title_elem.get_text().strip()
                raw_url = ""
                if link_elem and link_elem.get("href"):
                    raw_url = str(link_elem.get("href"))
                elif url_elem:
                    raw_url = url_elem.get_text().strip()
                resolved_url = self._resolve_url(raw_url)

                results.append(
                    {
                        "id": self._stable_id(title),
                        "title": title,
                        "authors": ["Web Source"],
                        "year": None,
                        "venue": "Web Search",
                        "doi_or_url": resolved_url,
                        "pdf_url": resolved_url if resolved_url.lower().endswith(".pdf") else None,
                        "abstract": snippet_elem.get_text().strip(),
                        "citation_count": 0,
                        "influential_citation_count": 0,
                    }
                )
        except Exception as exc:  # noqa: BLE001 - scraping is best-effort
            logger.warning("Web fallback search failed for %r: %s", query, exc)
        return results
