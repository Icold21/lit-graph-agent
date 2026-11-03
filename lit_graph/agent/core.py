from datetime import datetime, timezone
from typing import List, Set, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text

from ..config import settings
from ..llm.base import BaseLLMProvider
from ..models import GraphEdge, LiteratureBaseState, Paper
from ..search.engine import AcademicSearchEngine
from ..search.ranking import compute_scientific_metrics, find_elbow_cutoff
from ..storage.obsidian_vault import ObsidianVaultManager
from ..utils.logging_setup import get_logger
from .bus import AgentBus
from .evaluation_agent import EvaluationAgent
from .graph_agent import GraphAgent
from .prompt_agent import PromptAgent
from .retrieval_agent import RetrievalAgent
from .roles import TEAM_ROLES, get_role

console = Console()
logger = get_logger(__name__)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class LiteratureAgent:
    """Lead AI agent: coordinates the five role agents through the message bus."""

    role = TEAM_ROLES["lead"]

    def __init__(self, llm: BaseLLMProvider, search_engine: AcademicSearchEngine):
        self.llm = llm
        self.search_engine = search_engine
        self.bus = AgentBus()
        self.bus.register(RetrievalAgent(search_engine))
        self.bus.register(PromptAgent(llm))
        self.bus.register(EvaluationAgent())
        self.graph_agent: GraphAgent | None = None

    # ------------------------------------------------------------- orchestration
    def _open_vault(self, vault_path: str) -> ObsidianVaultManager:
        vault = ObsidianVaultManager(vault_path)
        self.graph_agent = GraphAgent(vault)
        self.bus.register(self.graph_agent)
        return vault

    def _collect_candidates(
        self, topic: str, requirements: str, max_papers: int
    ) -> Tuple[List[Paper], Set[str]]:
        """Iterative search + validation loop shared by create and update."""
        valid_candidates: List[Paper] = []
        seen_paper_ids: Set[str] = set()
        used_queries: List[str] = [topic]
        search_queries: List[str] = [topic]

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=25, style="cyan", complete_style="green"),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
            refresh_per_second=2,
            transient=True,
        ) as progress:
            search_task = progress.add_task("[yellow]рџ”Ќ Searching & validating papers...", total=max_papers)
            search_round = 1
            max_rounds = 3

            while len(valid_candidates) < max_papers and search_round <= max_rounds:
                if not search_queries:
                    generated = self.bus.request(
                        "retrieval",
                        "suggest_queries",
                        topic=topic,
                        requirements=requirements,
                        existing_queries=used_queries,
                    )
                    search_queries.extend(generated)
                    if not search_queries:
                        logger.warning("No further search queries could be generated")
                        break

                current_query = search_queries.pop(0)
                used_queries.append(current_query)
                raw_candidates = self.bus.request(
                    "retrieval",
                    "search",
                    query=current_query,
                    top_k=settings.max_search_candidates,
                )
                candidates_to_eval = [
                    raw for raw in raw_candidates if raw.get("id") not in seen_paper_ids
                ][: settings.candidate_eval_limit]

                for raw in candidates_to_eval:
                    seen_paper_ids.add(raw["id"])
                    paper = Paper(**raw)
                    if self.bus.request(
                        "llm",
                        "validate",
                        paper=paper,
                        topic=topic,
                        requirements=requirements,
                    ):
                        compute_scientific_metrics(paper)
                        valid_candidates.append(paper)
                        progress.update(search_task, completed=min(len(valid_candidates), max_papers))
                        if len(valid_candidates) >= max_papers:
                            break
                    else:
                        logger.info("Rejected %r: %s", paper.title, paper.topic_relevance_reason)

                search_round += 1

        return valid_candidates, seen_paper_ids

    def _ingest_paper(self, paper: Paper, state: LiteratureBaseState, deep_scan: bool) -> None:
        """Citation expansion + synthesis + optional deep PDF scan for one paper."""
        citation_data = self.bus.request(
            "retrieval",
            "expand_citations",
            paper_id=paper.id,
            limit=settings.citation_expansion_limit,
        )
        paper.referenced_paper_titles = citation_data.get("references", [])
        paper.citing_paper_titles = citation_data.get("citations", [])

        for reference in paper.referenced_paper_titles:
            state.add_edge(
                GraphEdge(source_title=paper.title, target_title=reference, relation_type="cites")
            )

        self.bus.request("llm", "synthesize_paper", paper=paper)

        if deep_scan:
            pages = self.bus.request(
                "retrieval",
                "fetch_pages",
                doi_or_url=paper.doi_or_url or "",
                pdf_url=paper.pdf_url,
            )
            if pages:
                self.bus.request("llm", "ground_concepts", paper=paper, pages=pages)
                del pages

        state.papers[paper.id] = paper

    def _audit(self, state: LiteratureBaseState, vault: ObsidianVaultManager) -> None:
        try:
            report = self.bus.request(
                "qa",
                "audit",
                state=state,
                vault_path=str(vault.vault_path),
            )
        except Exception as exc:  # noqa: BLE001 - QA must never break a run
            logger.error("QA audit failed: %s", exc)
            return

        if report.errors:
            console.print(
                f"[yellow]вљ  QA found {len(report.errors)} error(s) and "
                f"{len(report.warnings)} warning(s). See logs.[/yellow]"
            )
            for issue in report.errors[:5]:
                logger.error("QA %s: %s (%s)", issue.code, issue.message, issue.path)
        elif report.warnings:
            logger.info("QA audit: %s", report.summary())
        else:
            logger.info("QA audit passed: %s", report.summary())

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
                title=f"рџљЂ [bold green]LitGraphAgent Initializing: '{base_id}'[/bold green]",
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

        valid_candidates, _ = self._collect_candidates(topic, requirements, max_papers)
        if not valid_candidates:
            console.print("[red]вќЊ No papers passed validation.[/red]")
            self.flush_to_vault(state, vault)
            self._audit(state, vault)
            return state, vault

        # STEP 2: Ranking & Cutoff
        valid_candidates.sort(key=lambda item: item.objective_scientific_score, reverse=True)
        scores = [paper.objective_scientific_score for paper in valid_candidates]
        if settings.enable_elbow_cutoff:
            cutoff_k = find_elbow_cutoff(
                scores,
                min_k=min(len(scores), settings.min_papers_per_run),
                max_k=max_papers,
            )
        else:
            cutoff_k = min(len(scores), max_papers)
        selected_candidates = valid_candidates[:cutoff_k]

        # STEP 3: Paper Content Synthesis
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=25, style="cyan", complete_style="green"),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
            refresh_per_second=2,
            transient=True,
        ) as progress:
            synth_task = progress.add_task(
                "[magenta]рџ§  Ingesting selected papers...", total=len(selected_candidates)
            )
            for paper in selected_candidates:
                self._ingest_paper(paper, state, deep_scan)
                progress.advance(synth_task)

            self.bus.request("graph", "rebuild_graph", state=state, papers=selected_candidates)
            self.bus.request("graph", "save_state", state=state)

            # STEP 4: Batch Concept Synthesis & Master Files
            master_task = progress.add_task("[blue]рџ•ёпёЏ Synthesizing knowledge graph...", total=4)

            self.bus.request("llm", "define_concepts", state=state)
            progress.advance(master_task)

            self.bus.request("llm", "bibliography", state=state)
            progress.advance(master_task)

            self.bus.request("llm", "link_network", state=state)
            progress.advance(master_task)

            self.bus.request("llm", "overview", state=state)
            self.flush_to_vault(state, vault)
            progress.advance(master_task)

        self._audit(state, vault)

        # Output Summary Table
        table = Table(
            title=f"рџ“Љ Selected Papers ({len(selected_candidates)} chosen)", border_style="magenta"
        )
        table.add_column("Rank", justify="center")
        table.add_column("Title", style="white", max_width=45)
        table.add_column("Citations", justify="right", style="cyan")
        table.add_column("Score", justify="right", style="bold yellow")
        table.add_column("Weight (0-1)", justify="right", style="green")

        for index, paper in enumerate(selected_candidates, 1):
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
                title="вњЁ [bold green]Research Knowledge Graph Ready![/bold green]",
                border_style="green",
            )
        )
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
                title="рџ”„ [bold yellow]Expanding Literature Base[/bold yellow]",
                border_style="yellow",
            )
        )
        self.graph_agent = GraphAgent(vault)
        self.bus.register(self.graph_agent)
        state.updated_at = utc_now_iso()
        valid_candidates: List[Paper] = []
        seen_paper_ids: Set[str] = set(state.papers.keys())

        raw_candidates = self.bus.request(
            "retrieval",
            "search",
            query=directive_or_query,
            top_k=settings.max_search_candidates,
        )
        candidates_to_eval = [
            raw for raw in raw_candidates if raw.get("id") not in seen_paper_ids
        ][: settings.candidate_eval_limit]

        combined_topic = f"{state.topic} {directive_or_query}"
        for raw in candidates_to_eval:
            seen_paper_ids.add(raw["id"])
            paper = Paper(**raw)
            if self.bus.request(
                "llm",
                "validate",
                paper=paper,
                topic=combined_topic,
                requirements=state.requirements,
            ):
                compute_scientific_metrics(paper)
                valid_candidates.append(paper)
                if len(valid_candidates) >= max_new_papers:
                    break
            else:
                logger.info("Rejected %r: %s", paper.title, paper.topic_relevance_reason)

        if not valid_candidates:
            console.print("[yellow]No new candidates satisfied criteria.[/yellow]")
            self.bus.request("graph", "save_state", state=state)
            self._audit(state, vault)
            return state

        batch = valid_candidates[:max_new_papers]
        for paper in batch:
            self._ingest_paper(paper, state, deep_scan)

        self.bus.request("graph", "rebuild_graph", state=state, papers=list(state.papers.values()))
        self.bus.request("graph", "save_state", state=state)

        self.bus.request("llm", "define_concepts", state=state)
        self.bus.request("llm", "bibliography", state=state)
        self.bus.request("llm", "link_network", state=state)
        self.bus.request("llm", "overview", state=state)
        self.flush_to_vault(state, vault)
        self._audit(state, vault)

        console.print(
            f"[bold green]вњ“ Base successfully updated with {len(batch)} new nodes![/bold green]"
        )
        return state

    # ------------------------------------------------------------------- vault
    def flush_to_vault(self, state: LiteratureBaseState, vault: ObsidianVaultManager) -> None:
        if self.graph_agent is None or self.graph_agent.vault is not vault:
            self.graph_agent = GraphAgent(vault)
            self.bus.register(self.graph_agent)
        self.bus.request("graph", "flush", state=state, activity=self.bus.history)

    # -------------------------------------------------------------------- team
    def team_table(self) -> Table:
        table = Table(title="рџ¤– LitGraphAgent Team", border_style="cyan")
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

