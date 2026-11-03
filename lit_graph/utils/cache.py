import hashlib
import json
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

from .logging_setup import get_logger

logger = get_logger(__name__)


class FileCache:
    """Small JSON-on-disk cache used to avoid re-querying slow public APIs."""

    def __init__(self, root: Path | str, enabled: bool = True, ttl_seconds: int = 7 * 24 * 3600):
        self.root = Path(root)
        self.enabled = enabled
        self.ttl_seconds = ttl_seconds
        if self.enabled:
            try:
                self.root.mkdir(parents=True, exist_ok=True)
            except OSError as exc:  # pragma: no cover - filesystem specific
                logger.warning("Cache directory unavailable (%s); caching disabled", exc)
                self.enabled = False

    @staticmethod
    def _digest(namespace: str, key: Any) -> str:
        payload = json.dumps(key, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(f"{namespace}:{payload}".encode("utf-8")).hexdigest()

    def _path(self, namespace: str, key: Any) -> Path:
        return self.root / namespace / f"{self._digest(namespace, key)}.json"

    def get(self, namespace: str, key: Any) -> Any | None:
        if not self.enabled:
            return None
        path = self._path(namespace, key)
        try:
            if not path.exists():
                return None
            if self.ttl_seconds > 0 and (time.time() - path.stat().st_mtime) > self.ttl_seconds:
                path.unlink(missing_ok=True)
                return None
            with open(path, encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            logger.debug("Cache read failed for %s: %s", path, exc)
            return None

    def set(self, namespace: str, key: Any, value: Any) -> None:
        if not self.enabled:
            return
        path = self._path(namespace, key)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=False, default=str)
        except (OSError, TypeError) as exc:
            logger.debug("Cache write failed for %s: %s", path, exc)

    def clear(self, namespace: str | None = None) -> None:
        target = self.root / namespace if namespace else self.root
        if not target.exists():
            return
        for path in target.rglob("*.json"):
            try:
                path.unlink()
            except OSError:
                pass


@lru_cache(maxsize=1)
def get_cache() -> FileCache:
    from ..config import settings

    return FileCache(
        root=settings.cache_dir,
        enabled=settings.cache_enabled,
        ttl_seconds=max(0, settings.cache_ttl_hours) * 3600,
    )
