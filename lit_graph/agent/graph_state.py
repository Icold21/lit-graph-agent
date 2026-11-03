"""Shared state schema for the LangGraph research workflow.

Only JSON-serialisable values live here: the persistent literature base is
stored as a plain dict and re-hydrated into ``LiteratureBaseState`` inside the
nodes.  Runtime dependencies (LLM client, vault, agents) are owned by the
workflow object, not by the graph state.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any, Dict, List, TypedDict


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def merge_activity(left: List[Dict[str, Any]], right: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Reducer used by LangGraph to append agent events across nodes."""
    return [*(left or []), *(right or [])]


def make_event(
    recipient: str,
    action: str,
    *,
    sender: str = "lead",
    status: str = "ok",
    summary: str = "",
    duration_ms: int = 0,
) -> Dict[str, Any]:
    return {
        "sender": sender,
        "recipient": recipient,
        "action": action,
        "status": status,
        "timestamp": utc_now_iso(),
        "summary": summary[:240],
        "duration_ms": duration_ms,
    }


class ResearchState(TypedDict, total=False):
    """State passed between LangGraph nodes."""

    run_id: str
    mode: str  # "create" | "update"
    topic: str
    requirements: str
    directive: str
    max_papers: int
    deep_scan: bool
    base: Dict[str, Any]

    # Search planning
    plan_task: str
    plan_context: str
    plan_source: str
    plan_needs_llm: bool
    plan_decision: Any
    search_plan: Dict[str, Any]

    # Search / validation loop
    queries: List[str]
    used_queries: List[str]
    round: int
    candidates: List[Dict[str, Any]]
    valid_candidates: List[Dict[str, Any]]
    selected: List[Dict[str, Any]]
    seen_ids: List[str]

    # Ingestion
    ingest_index: int
    current_paper: Dict[str, Any]
    pages: Dict[str, str]

    # Results / observability
    graph_stats: Dict[str, int]
    qa_report: Dict[str, Any]
    activity: Annotated[List[Dict[str, Any]], merge_activity]
