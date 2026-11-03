"""Search-tool catalog.

Each backend is described in natural language so an LLM can choose the right
engine for a concrete research task instead of always querying everything.
The descriptions are also rendered by ``litgraph --team`` / logs, which keeps
the model's choice auditable by humans.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Tuple


@dataclass(frozen=True)
class SearchTool:
    """One selectable retrieval backend."""

    key: str
    label: str
    description: str
    strengths: Tuple[str, ...] = field(default_factory=tuple)
    limitations: Tuple[str, ...] = field(default_factory=tuple)
    best_for: Tuple[str, ...] = field(default_factory=tuple)
    returns_citations: bool = False
    returns_pdf: bool = False
    latency: str = "medium"

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # Tuples become lists so the structure survives JSON prompts and state.
        for key in ("strengths", "limitations", "best_for"):
            data[key] = list(data[key])
        return data

    def to_prompt_block(self) -> str:
        strengths = "; ".join(self.strengths) or "n/a"
        limitations = "; ".join(self.limitations) or "n/a"
        best_for = "; ".join(self.best_for) or "n/a"
        return (
            f"- `{self.key}` ({self.label})\n"
            f"  Description: {self.description}\n"
            f"  Strengths: {strengths}\n"
            f"  Limitations: {limitations}\n"
            f"  Best for: {best_for}\n"
            f"  Returns citation counts: {self.returns_citations} | "
            f"Open PDFs: {self.returns_pdf} | Latency: {self.latency}"
        )


SEARCH_TOOLS: Dict[str, SearchTool] = {
    "semantic_scholar": SearchTool(
        key="semantic_scholar",
        label="Semantic Scholar",
        description=(
            "Large cross-domain academic index (200M+ papers) with citation counts, "
            "influential-citation signals and a citation/reference graph. Best general-purpose "
            "scholarly search when impact or lineage matters."
        ),
        strengths=(
            "citation and influential-citation metadata",
            "citation/reference expansion",
            "cross-disciplinary coverage",
            "DOI and open-access PDF links",
        ),
        limitations=(
            "rate-limited without an API key",
            "weaker coverage of brand-new preprints",
            "abstracts are sometimes missing",
        ),
        best_for=(
            "established literature",
            "impact-aware ranking",
            "surveys and citation networks",
            "cross-domain topics",
        ),
        returns_citations=True,
        returns_pdf=True,
        latency="medium",
    ),
    "arxiv": SearchTool(
        key="arxiv",
        label="arXiv",
        description=(
            "Open preprint server for computer science, physics, mathematics, statistics and "
            "related fields. Strongest for cutting-edge, very recent and formula-heavy work; "
            "provides full-text PDFs but no citation counts and no peer-review guarantee."
        ),
        strengths=(
            "freshest preprints",
            "full-text PDFs",
            "LaTeX-heavy CS / physics / math coverage",
            "stable arXiv identifiers",
        ),
        limitations=(
            "no citation metrics",
            "not peer-reviewed",
            "weak for humanities, medicine and industry reports",
        ),
        best_for=(
            "state-of-the-art and recent preprints",
            "theoretical or mathematical topics",
            "deep PDF reading",
            "emerging subfields",
        ),
        returns_pdf=True,
        latency="low",
    ),
    "web": SearchTool(
        key="web",
        label="Open Web (DuckDuckGo)",
        description=(
            "General web search used as a last-resort fallback. Useful for gray literature, "
            "industry reports, documentation, policy papers and non-academic sources that do "
            "not live in scholarly indexes; results are noisy and lack reliable metadata."
        ),
        strengths=(
            "gray literature and industry sources",
            "documentation and technical reports",
            "finds PDFs hosted outside academic APIs",
        ),
        limitations=(
            "no citation metadata",
            "variable quality and duplicates",
            "possible SEO noise",
        ),
        best_for=(
            "industry / policy research",
            "applied engineering reports",
            "topics with thin academic coverage",
        ),
        returns_pdf=True,
        latency="medium",
    ),
}

DEFAULT_TOOL_ORDER: Tuple[str, ...] = ("semantic_scholar", "arxiv", "web")


def tool_catalog(keys: Tuple[str, ...] | None = None) -> list[SearchTool]:
    order = keys or DEFAULT_TOOL_ORDER
    return [SEARCH_TOOLS[key] for key in order if key in SEARCH_TOOLS]


def catalog_prompt(keys: Tuple[str, ...] | None = None) -> str:
    return "\n".join(tool.to_prompt_block() for tool in tool_catalog(keys))
