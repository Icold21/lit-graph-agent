"""Dynamic search-engine routing.

The model picks a retrieval strategy from the catalog in ``tools.py`` based on
the task description.  This module only *normalizes and validates* that choice
and provides a deterministic heuristic fallback when the LLM is unavailable or
returns something malformed - it never decides on its own when the model did
answer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Sequence

from ..utils.logging_setup import get_logger
from .tools import DEFAULT_TOOL_ORDER, SEARCH_TOOLS, SearchTool, tool_catalog

logger = get_logger(__name__)

_MAX_FALLBACKS = 2

_PREPRINT_SIGNALS = (
    "arxiv",
    "preprint",
    "state of the art",
    "state-of-the-art",
    "sota",
    "physics",
    "mathematics",
    "theoretical",
    "proof",
    "recent advances",
    "emerging",
)
_IMPACT_SIGNALS = (
    "survey",
    "systematic review",
    "meta-analysis",
    "citation",
    "influential",
    "impact",
    "peer-reviewed",
    "established",
    "benchmark",
    "dataset",
    "cross-domain",
)
_GRAY_SIGNALS = (
    "industry",
    "policy",
    "white paper",
    "whitepaper",
    "blog",
    "documentation",
    "technical report",
    "news",
    "gray literature",
    "grey literature",
    "market",
)


@dataclass
class SearchPlan:
    """A validated retrieval strategy."""

    primary: List[str]
    fallback: List[str] = field(default_factory=list)
    rationale: str = ""
    confidence: float = 0.5
    source: str = "llm"

    @property
    def engines(self) -> List[str]:
        """Primary + fallback in execution order."""
        return list(dict.fromkeys([*self.primary, *self.fallback]))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def describe(self) -> str:
        primary = ", ".join(self.primary) or "none"
        fallback = ", ".join(self.fallback) or "none"
        return f"primary={primary}; fallback={fallback}; source={self.source}"


class SearchRouter:
    """Validates model-produced engine choices and offers a heuristic fallback."""

    def __init__(
        self,
        available: Sequence[str] | None = None,
        max_primary: int = 2,
    ) -> None:
        keys = tuple(key for key in (available or DEFAULT_TOOL_ORDER) if key in SEARCH_TOOLS)
        self.tool_keys: tuple[str, ...] = keys or DEFAULT_TOOL_ORDER
        self.max_primary = max(1, max_primary)

    def catalog(self) -> List[SearchTool]:
        return tool_catalog(self.tool_keys)

    def catalog_prompt(self) -> str:
        return "\n".join(tool.to_prompt_block() for tool in self.catalog())

    def build_plan(
        self,
        decision: Any = None,
        *,
        task: str = "",
        requirements: str = "",
        source: str = "llm",
    ) -> SearchPlan:
        raw_primary, fallback = self._extract(decision)
        rationale, confidence = self._extract_meta(decision)

        if not raw_primary:
            return self.heuristic_plan(task, requirements, reason=self._invalid_reason(decision))

        primary = raw_primary[: self.max_primary]
        overflow = raw_primary[self.max_primary :]
        return self._finalize(
            primary=primary,
            fallback=[*fallback, *overflow],
            rationale=rationale or "Model selected engines from the tool catalog.",
            confidence=confidence,
            source=source,
        )

    def heuristic_plan(self, task: str, requirements: str, reason: str = "") -> SearchPlan:
        """Deterministic fallback used when the model cannot choose."""
        text = f"{task} {task} {requirements}".lower()
        gray = any(signal in text for signal in _GRAY_SIGNALS)
        preprint = any(signal in text for signal in _PREPRINT_SIGNALS)
        impact = any(signal in text for signal in _IMPACT_SIGNALS)

        if gray:
            primary = ["web"]
            fallback = ["semantic_scholar", "arxiv"]
            rationale = "Task mentions non-academic/gray sources, so the open web leads."
        elif preprint and not impact:
            primary = ["arxiv"]
            fallback = ["semantic_scholar", "web"]
            rationale = "Task targets recent preprints or formal/theoretical work, so arXiv leads."
        elif impact:
            primary = ["semantic_scholar"]
            fallback = ["arxiv", "web"]
            rationale = "Task needs citation-aware, established literature, so Semantic Scholar leads."
        else:
            primary = ["semantic_scholar", "arxiv"]
            fallback = ["web"]
            rationale = "No strong signal; use the two scholarly indexes and keep the web as fallback."

        plan = self._finalize(
            primary=[key for key in primary if key in self.tool_keys],
            fallback=[key for key in fallback if key in self.tool_keys],
            rationale=reason or rationale,
            confidence=0.4,
            source="heuristic",
        )
        logger.info("Heuristic search plan: %s", plan.describe())
        return plan

    def manual_plan(self, engines: Iterable[str]) -> SearchPlan:
        requested = [str(key).strip().lower() for key in engines if str(key).strip()]
        known = [key for key in requested if key in self.tool_keys]
        unknown = [key for key in requested if key not in self.tool_keys]
        if unknown:
            logger.warning("Ignoring unknown search engines: %s", ", ".join(unknown))
        if not known:
            return self.heuristic_plan("", "", reason="Manual engine override was empty or invalid.")
        return self._finalize(
            primary=known[: self.max_primary],
            fallback=known[self.max_primary :],
            rationale="Engine list provided manually via --engines.",
            confidence=1.0,
            source="manual",
        )

    # ------------------------------------------------------------------ helpers
    def _finalize(
        self,
        primary: List[str],
        fallback: List[str],
        *,
        rationale: str,
        confidence: float,
        source: str,
    ) -> SearchPlan:
        primary = list(dict.fromkeys(key for key in primary if key in self.tool_keys))
        if not primary:
            primary = [self.tool_keys[0]]

        fallback = [key for key in dict.fromkeys(fallback) if key in self.tool_keys and key not in primary]
        if not fallback:
            fallback = [key for key in self.tool_keys if key not in primary][:_MAX_FALLBACKS]
        else:
            fallback = fallback[:_MAX_FALLBACKS]

        return SearchPlan(
            primary=primary,
            fallback=fallback,
            rationale=rationale,
            confidence=max(0.0, min(1.0, confidence)),
            source=source,
        )

    @staticmethod
    def _invalid_reason(decision: Any) -> str:
        if decision is None:
            return "No model decision was available; using the heuristic search plan."
        if decision in ({}, [], ""):
            return "Model returned an empty engine choice; using the heuristic search plan."
        return "Model returned no usable engine names; using the heuristic search plan."

    def _extract(self, decision: Any) -> tuple[list[str], list[str]]:
        if decision is None:
            return [], []
        if isinstance(decision, str):
            return [decision], []
        if isinstance(decision, (list, tuple, set)):
            return [str(item) for item in decision], []
        if not isinstance(decision, dict):
            return [], []

        primary_raw = (
            decision.get("primary")
            or decision.get("engines")
            or decision.get("engine")
            or decision.get("selected")
        )
        fallback_raw = (
            decision.get("fallback")
            or decision.get("fallbacks")
            or decision.get("secondary")
            or decision.get("backup")
        )
        return self._as_list(primary_raw), self._as_list(fallback_raw)

    @staticmethod
    def _as_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, (list, tuple, set)):
            return [str(item) for item in value]
        return []

    @staticmethod
    def _extract_meta(decision: Any) -> tuple[str, float]:
        if not isinstance(decision, dict):
            return "", 0.4
        rationale = str(decision.get("rationale") or decision.get("reason") or "").strip()
        try:
            confidence = float(decision.get("confidence", 0.5))
        except (TypeError, ValueError):
            confidence = 0.5
        return rationale, confidence
