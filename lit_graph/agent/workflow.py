"""LangGraph orchestration of the five-role agent team.

The workflow replaces the former ``AgentBus``: every step is a node, every
hand-off is an edge, and the accumulated ``activity`` list is what the Graph
agent renders into ``_Agent_Activity.md``.  Business logic stays in the role
agents; nodes only move data between them.
"""

from __future__ import annotations

import time
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from ..config import settings
from ..models import GraphEdge, LiteratureBaseState, Paper
from ..search.ranking import compute_scientific_metrics, find_elbow_cutoff
from ..utils.logging_setup import get_logger
from .evaluation_agent import EvaluationAgent
from .graph_agent import GraphAgent
from .graph_state import ResearchState, make_event
from .prompt_agent import PromptAgent
from .retrieval_agent import RetrievalAgent

logger = get_logger(__name__)

MAX_SEARCH_ROUNDS = 3


class LiteratureWorkflow:
    """Builds and runs the ``create`` and ``update`` LangGraph workflows."""

    def __init__(
        self,
        *,
        retrieval: RetrievalAgent,
        prompt: PromptAgent,
        evaluation: EvaluationAgent,
        graph_agent: GraphAgent,
        on_plan: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        self.retrieval = retrieval
        self.prompt = prompt
        self.evaluation = evaluation
        self.graph_agent = graph_agent
        self.on_plan = on_plan

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _base(state: ResearchState) -> LiteratureBaseState:
        return LiteratureBaseState(**state["base"])

    @staticmethod
    def _dump(base: LiteratureBaseState) -> Dict[str, Any]:
        return base.model_dump(mode="json")

    @staticmethod
    def _papers(items: List[Dict[str, Any]]) -> List[Paper]:
        return [Paper(**item) for item in items]

    @staticmethod
    def _summarize(patch: Dict[str, Any]) -> str:
        parts: List[str] = []
        plan = patch.get("search_plan")
        if plan:
            parts.append("engines=" + ",".join(plan.get("primary", [])))
        for key in ("candidates", "valid_candidates", "selected"):
            if key in patch:
                parts.append(f"{key}={len(patch[key] or [])}")
        if "pages" in patch:
            parts.append(f"pages={len(patch['pages'] or {})}")
        if "ingest_index" in patch:
            parts.append(f"ingest_index={patch['ingest_index']}")
        base = patch.get("base")
        if base:
            parts.append(
                f"papers={len(base.get('papers', {}))},concepts={len(base.get('concepts', {}))}"
            )
        if patch.get("qa_report"):
            parts.append("qa=" + str(patch["qa_report"].get("summary", "")))
        return "; ".join(parts)

    def _step(self, recipient: str, action: str, fn: Callable[[ResearchState], Dict[str, Any]]):
        """Wrap a node so each execution appends one activity event."""

        @wraps(fn)
        def node(state: ResearchState) -> Dict[str, Any]:
            started = time.perf_counter()
            try:
                patch = fn(state) or {}
            except Exception as exc:
                elapsed = int((time.perf_counter() - started) * 1000)
                logger.error("LangGraph node %s failed: %s", action, exc)
                raise
            elapsed = int((time.perf_counter() - started) * 1000)
            patch = dict(patch)
            patch["activity"] = [
                make_event(recipient, action, summary=self._summarize(patch), duration_ms=elapsed)
            ]
            return patch

        return node

    # ------------------------------------------------------------- plan nodes
    def _plan_request(self, state: ResearchState) -> Dict[str, Any]:
        request = self.retrieval.plan_request(
            state["plan_task"],
            state["requirements"],
            state.get("plan_context", ""),
        )
        return {"plan_needs_llm": bool(request["needs_llm"]), "plan_source": request["source"]}

    def _choose_engines(self, state: ResearchState) -> Dict[str, Any]:
        decision = self.prompt.choose_engines(
            task=state["plan_task"],
            requirements=state["requirements"],
            catalog=self.retrieval.catalog_prompt(),
            context=state.get("plan_context", ""),
        )
        return {"plan_decision": decision}

    def _finalize_plan(self, state: ResearchState) -> Dict[str, Any]:
        plan = self.retrieval.finalize_plan(
            state.get("plan_decision"),
            task=state["plan_task"],
            requirements=state["requirements"],
            source=state.get("plan_source", "llm"),
        )
        base = self._base(state)
        base.search_plan = plan
        if self.on_plan is not None:
            self.on_plan(plan)
        return {"search_plan": plan, "base": self._dump(base)}

    # ------------------------------------------------------------ search nodes
    def _search(self, state: ResearchState) -> Dict[str, Any]:
        queries = list(state.get("queries") or [])
        if not queries:
            return {"candidates": []}

        query = queries.pop(0)
        plan = state.get("search_plan") or {}
        raw_candidates = self.retrieval.search(
            query,
            top_k=settings.max_search_candidates,
            engines=plan.get("primary") or None,
            fallback_engines=plan.get("fallback") or None,
            min_results=settings.search_fallback_min_results,
        )

        seen = set(state.get("seen_ids") or [])
        fresh = [raw for raw in raw_candidates if raw.get("id") not in seen]
        fresh = fresh[: settings.candidate_eval_limit]
        seen.update(raw["id"] for raw in fresh if raw.get("id"))

        return {
            "queries": queries,
            "used_queries": [*(state.get("used_queries") or []), query],
            "candidates": fresh,
            "seen_ids": sorted(seen),
            "round": int(state.get("round", 0)) + 1,
        }

    def _validate(self, state: ResearchState) -> Dict[str, Any]:
        valid = self._papers(state.get("valid_candidates") or [])
        max_papers = int(state["max_papers"])

        for raw in state.get("candidates") or []:
            paper = Paper(**raw)
            if self.prompt.validate_candidate(
                paper, topic=state["topic"], requirements=state["requirements"]
            ):
                compute_scientific_metrics(paper)
                valid.append(paper)
                if len(valid) >= max_papers:
                    break
            else:
                logger.info("Rejected %r: %s", paper.title, paper.topic_relevance_reason)

        patch: Dict[str, Any] = {
            "valid_candidates": [paper.model_dump(mode="json") for paper in valid],
            "candidates": [],
        }
        if state.get("mode") == "update":
            patch["selected"] = patch["valid_candidates"]
        return patch

    def _suggest_queries(self, state: ResearchState) -> Dict[str, Any]:
        generated = self.prompt.generate_sub_queries(
            topic=state["topic"],
            requirements=state["requirements"],
            existing_queries=list(state.get("used_queries") or []),
        )
        if not generated:
            logger.warning("No further search queries could be generated")
        return {"queries": generated}

    def _rank_select(self, state: ResearchState) -> Dict[str, Any]:
        candidates = self._papers(state.get("valid_candidates") or [])
        candidates.sort(key=lambda item: item.objective_scientific_score, reverse=True)
        scores = [paper.objective_scientific_score for paper in candidates]
        if not scores:
            return {"selected": []}

        if settings.enable_elbow_cutoff:
            cutoff_k = find_elbow_cutoff(
                scores,
                min_k=min(len(scores), settings.min_papers_per_run),
                max_k=int(state["max_papers"]),
            )
        else:
            cutoff_k = min(len(scores), int(state["max_papers"]))
        selected = candidates[:cutoff_k]
        for paper in selected:
            paper.is_elbow_selected = True
        return {"selected": [paper.model_dump(mode="json") for paper in selected]}

    # ----------------------------------------------------------- ingest nodes
    def _expand_citations(self, state: ResearchState) -> Dict[str, Any]:
        index = int(state.get("ingest_index", 0))
        selected = state.get("selected") or []
        paper = Paper(**selected[index])

        citation_data = self.retrieval.expand_citations(
            paper.id, limit=settings.citation_expansion_limit
        )
        paper.referenced_paper_titles = citation_data.get("references", [])
        paper.citing_paper_titles = citation_data.get("citations", [])

        base = self._base(state)
        for reference in paper.referenced_paper_titles:
            base.add_edge(
                GraphEdge(source_title=paper.title, target_title=reference, relation_type="cites")
            )
        return {"current_paper": paper.model_dump(mode="json"), "base": self._dump(base)}

    def _synthesize(self, state: ResearchState) -> Dict[str, Any]:
        paper = Paper(**state["current_paper"])
        self.prompt.synthesize_paper(paper)
        return {"current_paper": paper.model_dump(mode="json")}

    def _fetch_pages(self, state: ResearchState) -> Dict[str, Any]:
        paper = Paper(**state["current_paper"])
        pages = self.retrieval.fetch_pages(
            paper.doi_or_url or "",
            pdf_url=paper.pdf_url,
        )
        return {"pages": pages}

    def _ground_concepts(self, state: ResearchState) -> Dict[str, Any]:
        paper = Paper(**state["current_paper"])
        pages = {int(page): text for page, text in (state.get("pages") or {}).items()}
        self.prompt.ground_concepts(paper, pages)
        return {"current_paper": paper.model_dump(mode="json"), "pages": {}}

    def _commit_paper(self, state: ResearchState) -> Dict[str, Any]:
        paper = Paper(**state["current_paper"])
        base = self._base(state)
        base.papers[paper.id] = paper
        return {"base": self._dump(base), "ingest_index": int(state.get("ingest_index", 0)) + 1}

    # ---------------------------------------------------------- knowledge nodes
    def _rebuild_graph(self, state: ResearchState) -> Dict[str, Any]:
        base = self._base(state)
        if state.get("mode") == "create":
            # Reuse the objects that were committed into the base so concept
            # canonicalization and node weights are persisted back.
            papers = [
                base.papers[item["id"]]
                for item in (state.get("selected") or [])
                if item.get("id") in base.papers
            ]
        else:
            papers = list(base.papers.values())

        stats = self.graph_agent.rebuild_graph(base, papers)
        self.graph_agent.vault.save_state(base)
        return {"graph_stats": stats, "base": self._dump(base)}

    def _define_concepts(self, state: ResearchState) -> Dict[str, Any]:
        base = self._base(state)
        self.prompt.define_concepts(base)
        return {"base": self._dump(base)}

    def _bibliography(self, state: ResearchState) -> Dict[str, Any]:
        base = self._base(state)
        self.prompt.build_bibliography(base)
        return {"base": self._dump(base)}

    def _link_network(self, state: ResearchState) -> Dict[str, Any]:
        base = self._base(state)
        self.prompt.link_network(base)
        return {"base": self._dump(base)}

    def _overview(self, state: ResearchState) -> Dict[str, Any]:
        base = self._base(state)
        self.prompt.build_overview(base)
        return {"base": self._dump(base)}

    def _flush(self, state: ResearchState) -> Dict[str, Any]:
        base = self._base(state)
        self.graph_agent.flush(base, activity=state.get("activity") or [])
        return {"base": self._dump(base)}

    def _save_state(self, state: ResearchState) -> Dict[str, Any]:
        base = self._base(state)
        self.graph_agent.vault.save_state(base)
        return {"base": self._dump(base)}

    def _audit(self, state: ResearchState) -> Dict[str, Any]:
        base = self._base(state)
        report = self.evaluation.audit(base, str(self.graph_agent.vault.vault_path))
        return {"qa_report": report.to_dict()}

    # ------------------------------------------------------------- routing
    @staticmethod
    def _after_plan_request(state: ResearchState) -> str:
        return "choose_engines" if state.get("plan_needs_llm") else "finalize_plan"

    @staticmethod
    def _after_validate_create(state: ResearchState) -> str:
        if (
            len(state.get("valid_candidates") or []) >= int(state["max_papers"])
            or int(state.get("round", 0)) >= MAX_SEARCH_ROUNDS
        ):
            return "rank_select"
        return "search" if state.get("queries") else "suggest_queries"

    @staticmethod
    def _after_suggest(state: ResearchState) -> str:
        return "search" if state.get("queries") else "rank_select"

    @staticmethod
    def _after_rank(state: ResearchState) -> str:
        return "expand_citations" if state.get("selected") else "flush"

    @staticmethod
    def _after_validate_update(state: ResearchState) -> str:
        return "expand_citations" if state.get("selected") else "save_state"

    @staticmethod
    def _after_synthesize(state: ResearchState) -> str:
        return "fetch_pages" if state.get("deep_scan") else "commit_paper"

    @staticmethod
    def _after_fetch(state: ResearchState) -> str:
        return "ground_concepts" if state.get("pages") else "commit_paper"

    @staticmethod
    def _after_commit(state: ResearchState) -> str:
        index = int(state.get("ingest_index", 0))
        return "expand_citations" if index < len(state.get("selected") or []) else "rebuild_graph"

    # --------------------------------------------------------------- build
    def _register_nodes(self, graph: StateGraph) -> None:
        graph.add_node("plan_request", self._step("retrieval", "plan_search", self._plan_request))
        graph.add_node(
            "choose_engines",
            self._step("llm", "select_search_engines", self._choose_engines),
        )
        graph.add_node(
            "finalize_plan", self._step("retrieval", "finalize_plan", self._finalize_plan)
        )
        graph.add_node("search", self._step("retrieval", "search", self._search))
        graph.add_node("validate", self._step("llm", "validate", self._validate))
        graph.add_node(
            "suggest_queries", self._step("llm", "generate_sub_queries", self._suggest_queries)
        )
        graph.add_node("rank_select", self._step("lead", "rank_select", self._rank_select))
        graph.add_node(
            "expand_citations",
            self._step("retrieval", "expand_citations", self._expand_citations),
        )
        graph.add_node("synthesize", self._step("llm", "synthesize_paper", self._synthesize))
        graph.add_node("fetch_pages", self._step("retrieval", "fetch_pages", self._fetch_pages))
        graph.add_node(
            "ground_concepts", self._step("llm", "ground_concepts", self._ground_concepts)
        )
        graph.add_node("commit_paper", self._step("lead", "commit_paper", self._commit_paper))
        graph.add_node(
            "rebuild_graph", self._step("graph", "rebuild_graph", self._rebuild_graph)
        )
        graph.add_node(
            "define_concepts", self._step("llm", "define_concepts", self._define_concepts)
        )
        graph.add_node("bibliography", self._step("llm", "bibliography", self._bibliography))
        graph.add_node("link_network", self._step("llm", "link_network", self._link_network))
        graph.add_node("overview", self._step("llm", "overview", self._overview))
        graph.add_node("flush", self._step("graph", "flush", self._flush))
        graph.add_node("save_state", self._step("graph", "save_state", self._save_state))
        graph.add_node("audit", self._step("qa", "audit", self._audit))

    def _add_tail(self, graph: StateGraph) -> None:
        graph.add_edge("rebuild_graph", "define_concepts")
        graph.add_edge("define_concepts", "bibliography")
        graph.add_edge("bibliography", "link_network")
        graph.add_edge("link_network", "overview")
        graph.add_edge("overview", "flush")
        graph.add_edge("flush", "audit")
        graph.add_edge("audit", END)

    def build(self, mode: str = "create"):
        """Compile a workflow with an in-memory checkpointer."""
        graph = StateGraph(ResearchState)
        self._register_nodes(graph)

        graph.add_edge(START, "plan_request")
        graph.add_conditional_edges(
            "plan_request",
            self._after_plan_request,
            {"choose_engines": "choose_engines", "finalize_plan": "finalize_plan"},
        )
        graph.add_edge("choose_engines", "finalize_plan")
        graph.add_edge("finalize_plan", "search")
        graph.add_edge("search", "validate")

        if mode == "update":
            graph.add_conditional_edges(
                "validate",
                self._after_validate_update,
                {"expand_citations": "expand_citations", "save_state": "save_state"},
            )
            graph.add_edge("save_state", "audit")
        else:
            graph.add_conditional_edges(
                "validate",
                self._after_validate_create,
                {
                    "search": "search",
                    "suggest_queries": "suggest_queries",
                    "rank_select": "rank_select",
                },
            )
            graph.add_conditional_edges(
                "suggest_queries",
                self._after_suggest,
                {"search": "search", "rank_select": "rank_select"},
            )
            graph.add_conditional_edges(
                "rank_select",
                self._after_rank,
                {"expand_citations": "expand_citations", "flush": "flush"},
            )

        graph.add_edge("expand_citations", "synthesize")
        graph.add_conditional_edges(
            "synthesize",
            self._after_synthesize,
            {"fetch_pages": "fetch_pages", "commit_paper": "commit_paper"},
        )
        graph.add_conditional_edges(
            "fetch_pages",
            self._after_fetch,
            {"ground_concepts": "ground_concepts", "commit_paper": "commit_paper"},
        )
        graph.add_edge("ground_concepts", "commit_paper")
        graph.add_conditional_edges(
            "commit_paper",
            self._after_commit,
            {"expand_citations": "expand_citations", "rebuild_graph": "rebuild_graph"},
        )

        self._add_tail(graph)
        return graph.compile(checkpointer=MemorySaver())


__all__ = ["LiteratureWorkflow"]
