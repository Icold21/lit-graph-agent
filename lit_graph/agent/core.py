from datetime import datetime, timezone
from typing import Any, Dict, Tuple
from uuid import uuid4

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text

from ..config import settings
from ..llm.base import BaseLLMProvider
from ..models import LiteratureBaseState
from ..search.engine import AcademicSearchEngine
from ..storage.obsidian_vault import ObsidianVaultManager
from ..utils.logging_setup import get_logger
from .evaluation_agent import EvaluationAgent
from .graph_agent import GraphAgent
from .graph_state import ResearchState
from .prompt_agent import PromptAgent
from .retrieval_agent import RetrievalAgent
from .roles import TEAM_ROLES, get_role
from .workflow import LiteratureWorkflow

console = Console()
logger = get_logger(__name__)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class LiteratureAgent:
    """Lead AI agent: runs the five-role LangGraph research workflow."""

    role = TEAM_ROLES["lead"]

    def __init__(self, llm: BaseLLMProvider, search_engine: AcademicSearchEngine):
        self.llm = llm
        self.search_engine = search_engine
        self.retrieval = RetrievalAgent(search_engine)
        self.prompt = PromptAgent(llm)
        self.evaluation = EvaluationAgent()
        self.graph_agent: GraphAgent | None = None

        self.last_search_plan: Dict[str, Any] = {}
        self.activity: list[Dict[str, Any]] = []
        self.last_qa_report: Dict[str, Any] | None = None

    # ------------------------------------------------------------- orchestration
    def _open_vault(self, vault_path: str) -> ObsidianVaultManager:
        vault = ObsidianVaultManager(vault_path)
        self.graph_agent = GraphAgent(vault)
        return vault

    def _bind_vault(self, vault: ObsidianVaultManager) -> None:
        if self.graph_agent is None or self.graph_agent.vault is not vault:
            self.graph_agent = GraphAgent(vault)

    def _display_plan(self, plan: Dict[str, Any]) -> None:
        primary = ", ".join(plan.get("primary", [])) or "auto"
        fallback = ", ".join(plan.get("fallback", [])) or "none"
        console.print(
            f"[bold cyan]Search strategy:[/bold cyan] primary=[green]{primary}[/green] "
            f"fallback=[dim]{fallback}[/dim] "
            f"[dim]({plan.get('source', 'heuristic')})[/dim]"
        )
        if plan.get("rationale"):
            console.print(f"[dim]  {plan['rationale']}[/dim]")

    def _run_graph(
        self,
        *,
        mode: str,
        base: LiteratureBaseState,
        topic: str,
        requirements: str,
        directive: str,
        max_papers: int,
        deep_scan: bool,
    ) -> Dict[str, Any]:
        """Run the compiled LangGraph workflow and return its final state."""
        if self.graph_agent is None:
            raise RuntimeError("Graph agent is not bound to a vault")

        workflow = LiteratureWorkflow(
            retrieval=self.retrieval,
            prompt=self.prompt,
            evaluation=self.evaluation,
            graph_agent=self.graph_agent,
            on_plan=self._display_plan,
        )
        graph = workflow.build(mode)

        run_id = f"{base.base_id}-{uuid4().hex[:8]}"
        config = {
            "configurable": {"thread_id": run_id},
            "recursion_limit": 200,
        }
        initial: ResearchState = {
            "run_id": run_id,
            "mode": mode,
            "topic": topic,
            "requirements": requirements,
            "directive": directive,
            "max_papers": max_papers,
            "deep_scan": deep_scan,
            "base": base.model_dump(mode="json"),
            "plan_task": f"{topic} {directive}".strip(),
            "plan_context": (
                f"Existing base '{base.base_id}' with {len(base.papers)} papers."
                if mode == "update"
                else ""
            ),
            "queries": [directive] if mode == "update" else [topic],
            "used_queries": [],
            "round": 0,
            "candidates": [],
            "valid_candidates": [],
            "selected": [],
            "seen_ids": list(base.papers.keys()) if mode == "update" else [],
            "ingest_index": 0,
            "activity": [],
        }

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            TimeElapsedColumn(),
            console=console,
            refresh_per_second=4,
            transient=True,
        ) as progress:
            task = progress.add_task("[cyan]LangGraph: starting workflow...", total=None)
            for chunk in graph.stream(initial, config=config, stream_mode="updates"):
                for node_name in chunk:
                    progress.update(
                        task,
                        description=f"[cyan]LangGraph → [bold]{node_name}[/bold]",
                    )

        final = graph.get_state(config).values
        self.activity = list(final.get("activity") or [])
        self.last_search_plan = final.get("search_plan") or base.search_plan
        self.last_qa_report = final.get("qa_report")
        return dict(final)

    def _report_qa(self) -> None:
        report = self.last_qa_report or {}
        errors = [issue for issue in report.get("issues", []) if issue.get("severity") == "error"]
        warnings = [
            issue for issue in report.get("issues", []) if issue.get("severity") == "warning"
        ]
        if errors:
            console.print(
                f"[yellow]⚠ QA found {len(errors)} error(s) and {len(warnings)} warning(s). "
                "See logs.[/yellow]"
            )
            for issue in errors[:5]:
                logger.error("QA %s: %s (%s)", issue.get("code"), issue.get("message"), issue.get("path"))
        else:
            logger.info("QA audit: %s", report.get("summary", "not available"))

    # ------------------------------------------------------------------ create
    def initialize_base(
        self,
        base_id: str,
        topic: str,
        requirements: str,
        citation_format: str,
        vault_path: str,
        max_papers: int = settings.max_papers_per_run,
        deep_scan: bool = False,
    ) -> Tuple[LiteratureBaseState, ObsidianVaultManager]:
        mode_label = (
            "[bold red]DEEP PDF MODE[/bold red]"
            if deep_scan
            else "[bold green]FAST MODE (Abstract-based)[/bold green]"
        )
        console.print(
            Panel(
                f"[bold cyan]Topic:[/bold cyan] {topic}\n"
                f"[bold yellow]Requirements:[/bold yellow] {requirements}\n"
                f"[bold green]Vault Target:[/bold green] {vault_path}\n"
                f"[bold magenta]Target Papers Goal:[/bold magenta] {max_papers} | [bold blue]Mode:[/bold blue] {mode_label}",
                title=f"🚀 [bold green]LitGraphAgent Initializing: '{base_id}'[/bold green]",
                border_style="cyan",
            )
        )

        vault = self._open_vault(vault_path)
        state = LiteratureBaseState(
            base_id=base_id,
            topic=topic,
            requirements=requirements,
            citation_format=citation_format,
            created_at=utc_now_iso(),
            updated_at=utc_now_iso(),
        )

        final = self._run_graph(
            mode="create",
            base=state,
            topic=topic,
            requirements=requirements,
            directive="",
            max_papers=max_papers,
            deep_scan=deep_scan,
        )
        state = LiteratureBaseState(**final["base"])
        selected_count = len(final.get("selected") or [])

        if not state.papers:
            console.print("[red]❌ No papers passed validation.[/red]")
            self._report_qa()
            return state, vault

        table = Table(
            title=f"📊 Selected Papers ({selected_count} chosen)", border_style="magenta"
        )
        table.add_column("Rank", justify="center")
        table.add_column("Title", style="white", max_width=45)
        table.add_column("Citations", justify="right", style="cyan")
        table.add_column("Score", justify="right", style="bold yellow")
        table.add_column("Weight (0-1)", justify="right", style="green")

        selected = [state.papers[item["id"]] for item in (final.get("selected") or []) if item["id"] in state.papers]
        for index, paper in enumerate(selected, 1):
            table.add_row(
                str(index),
                paper.title,
                str(paper.citation_count),
                f"{paper.objective_scientific_score:.2f}",
                f"{paper.normalized_weight:.3f}",
            )
        console.print(table)

        console.print(
            Panel(
                f"[bold green]Vault Location:[/bold green] {vault_path}\n"
                f"[bold cyan]Total Verified Sources:[/bold cyan] {len(state.papers)}\n"
                f"[bold magenta]Full Concept Hubs Created:[/bold magenta] {len(state.concepts)}\n"
                f"[bold yellow]Graph Connections:[/bold yellow] {len(state.edges)}",
                title="✨ [bold green]Research Knowledge Graph Ready![/bold green]",
                border_style="green",
            )
        )
        self._report_qa()
        return state, vault

    # ------------------------------------------------------------------ update
    def update_base(
        self,
        state: LiteratureBaseState,
        vault: ObsidianVaultManager,
        directive_or_query: str,
        max_new_papers: int = settings.max_papers_per_run,
        deep_scan: bool = False,
    ) -> LiteratureBaseState:
        console.print(
            Panel(
                f"[bold yellow]Directive:[/bold yellow] {directive_or_query}\n"
                f"[bold cyan]Base:[/bold cyan] {state.base_id}",
                title="🔄 [bold yellow]Expanding Literature Base[/bold yellow]",
                border_style="yellow",
            )
        )
        self._bind_vault(vault)
        state.updated_at = utc_now_iso()
        combined_topic = f"{state.topic} {directive_or_query}"
        before = len(state.papers)

        final = self._run_graph(
            mode="update",
            base=state,
            topic=combined_topic,
            requirements=state.requirements,
            directive=directive_or_query,
            max_papers=max_new_papers,
            deep_scan=deep_scan,
        )
        updated = LiteratureBaseState(**final["base"])
        added = len(updated.papers) - before

        if added <= 0:
            console.print("[yellow]No new candidates satisfied criteria.[/yellow]")
        else:
            console.print(
                f"[bold green]✓ Base successfully updated with {added} new nodes![/bold green]"
            )
        self._report_qa()
        return updated

    # ------------------------------------------------------------------- vault
    def flush_to_vault(self, state: LiteratureBaseState, vault: ObsidianVaultManager) -> None:
        self._bind_vault(vault)
        if self.graph_agent is None:
            raise RuntimeError("Graph agent is not bound to a vault")
        self.graph_agent.flush(state, activity=self.activity)

    # -------------------------------------------------------------------- team
    def team_table(self) -> Table:
        table = Table(title="🤖 LitGraphAgent Team", border_style="cyan")
        table.add_column("Role", style="bold")
        table.add_column("Owner")
        table.add_column("Agent", style="green")
        table.add_column("Responsibility", style="white")
        for key in ("lead", "graph", "retrieval", "qa", "llm"):
            role = get_role(key)
            table.add_row(
                role.title,
                f"{role.owner} ({role.handle})",
                role.agent,
                Text(role.responsibility),
            )
        return table
