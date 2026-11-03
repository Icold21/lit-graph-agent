import io
from typing import Dict, Optional

from pypdf import PdfReader

from ..utils.http import request_with_retry
from ..utils.logging_setup import get_logger

logger = get_logger(__name__)

MAX_PDF_BYTES = 40 * 1024 * 1024


class EphemeralPDFReader:
    """Streams and extracts page-level text into ephemeral memory, immediately freeing RAM."""

    @staticmethod
    def _resolve_pdf_url(doi_or_url: str) -> Optional[str]:
        if not doi_or_url:
            return None
        url = doi_or_url.strip()
        if "arxiv.org/abs/" in url:
            return url.replace("arxiv.org/abs/", "arxiv.org/pdf/") + ".pdf"
        if "arxiv.org/pdf/" in url:
            return url if url.endswith(".pdf") else f"{url}.pdf"
        if url.lower().endswith(".pdf"):
            return url
        return None

    def fetch_pages(self, doi_or_url: str, max_pages: int = 15, pdf_url: str | None = None) -> Dict[int, str]:
        resolved = pdf_url or self._resolve_pdf_url(doi_or_url)
        if not resolved:
            return {}

        pages_text: Dict[int, str] = {}
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            response = request_with_retry("GET", resolved, headers=headers, timeout=45)
            if response is None or response.status_code != 200:
                logger.info("PDF download failed for %s", resolved)
                return {}

            content = response.content
            if len(content) > MAX_PDF_BYTES:
                logger.warning("PDF at %s exceeds %s bytes; skipping deep scan", resolved, MAX_PDF_BYTES)
                return {}

            with io.BytesIO(content) as buffer:
                reader = PdfReader(buffer)
                total_pages = min(len(reader.pages), max_pages)
                for index in range(total_pages):
                    text = reader.pages[index].extract_text() or ""
                    if len(text.strip()) > 50:
                        pages_text[index + 1] = text.strip()
        except Exception as exc:  # noqa: BLE001 - malformed PDFs are common
            logger.warning("PDF extraction failed for %s: %s", resolved, exc)

        return pages_text
