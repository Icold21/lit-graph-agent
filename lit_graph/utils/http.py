import time
from typing import Any

import requests

from .logging_setup import get_logger

logger = get_logger(__name__)

RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


def request_with_retry(
    method: str,
    url: str,
    *,
    timeout: float | None = None,
    retries: int | None = None,
    **kwargs: Any,
) -> requests.Response | None:
    """HTTP request with exponential backoff for rate limits and transient errors.

    Returns ``None`` when every attempt failed. Non-retryable responses are
    returned as-is so callers can inspect the status code.
    """
    from ..config import settings

    timeout = settings.http_timeout if timeout is None else timeout
    retries = max(1, settings.http_max_retries if retries is None else retries)

    for attempt in range(retries):
        try:
            response = requests.request(method, url, timeout=timeout, **kwargs)
        except requests.RequestException as exc:
            logger.warning("%s %s failed (attempt %s/%s): %s", method, url, attempt + 1, retries, exc)
            if attempt + 1 < retries:
                time.sleep(min(2**attempt, 8))
            continue

        if response.status_code not in RETRYABLE_STATUSES:
            return response

        retry_after = response.headers.get("Retry-After")
        delay = min(2**attempt, 15)
        if retry_after:
            try:
                delay = max(delay, min(float(retry_after), 30))
            except ValueError:
                pass
        logger.warning(
            "%s %s returned HTTP %s (attempt %s/%s), retrying in %.1fs",
            method,
            url,
            response.status_code,
            attempt + 1,
            retries,
            delay,
        )
        if attempt + 1 < retries:
            time.sleep(delay)

    return None
