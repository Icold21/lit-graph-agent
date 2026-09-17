import io
import requests
from typing import Dict, Optional
from pypdf import PdfReader


class EphemeralPDFReader:
    """Streams and extracts page-level text into ephemeral memory, immediately freeing RAM."""

    @staticmethod
    def _resolve_pdf_url(doi_or_url: str) -> Optional[str]:
        if not doi_or_url:
            return None
        # Convert arXiv abstract URL to direct PDF stream URL
        if "arxiv.org/abs/" in doi_or_url:
            return doi_or_url.replace("arxiv.org/abs/", "arxiv.org/pdf/") + ".pdf"
        if doi_or_url.endswith(".pdf"):
            return doi_or_url
        return None

    def fetch_pages(self, doi_or_url: str, max_pages: int = 15) -> Dict[int, str]:
        pdf_url = self._resolve_pdf_url(doi_or_url)
        if not pdf_url:
            return {}

        pages_text: Dict[int, str] = {}
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            resp = requests.get(pdf_url, headers=headers, timeout=12)
            if resp.status_code == 200:
                with io.BytesIO(resp.content) as buffer:
                    reader = PdfReader(buffer)
                    total_pages = min(len(reader.pages), max_pages)
                    for idx in range(total_pages):
                        text = reader.pages[idx].extract_text() or ""
                        if len(text.strip()) > 50:
                            pages_text[idx + 1] = text.strip()
        except Exception:
            pass
        
        return pages_text