from datetime import datetime
from typing import List, Set
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

from ..config import settings
from ..llm.base import BaseLLMProvider
from ..models import Paper, LiteratureBaseState, GraphEdge
from ..search.engine import AcademicSearchEngine
from ..search.ranking import compute_scientific_metrics, find_elbow_cutoff
from .validator import LiteratureValidator
from .synthesizer import LiteratureSynthesizer
from ..storage.obsidian_vault import ObsidianVaultManager

console = Console(force_terminal=True)


class LiteratureAgent:
    """Fast Optimized Research Agent with smooth Progress Bar and Adaptive Search."""

    def __init__(self, llm: BaseLLMProvider, search_engine: AcademicSearchEngine):
        self.llm = llm
        self.search_engine = search_engine
        self.validator = LiteratureValidator(llm)
        self.synthesizer = LiteratureSynthesizer(llm)

    def _generate_sub_queries(self, topic: str, requirements: str, existing_queries: List[str]) -> List[str]:
        prompt = f"""
Topic: {topic}
Requirements: {requirements}
Used: {existing_queries}

Generate 2 distinct academic search queries in JSON:
{{"queries": ["query 1", "query 2"]}}
"""
        res = self.llm.generate_json(prompt, "Expert research librarian. Output only JSON.")
        return res.get("queries", [])[:2]

    def initialize_base(
        self,
        base_id: str,
        topic: str,
        requirements: str,
        citation_format: str,
        vault_path: str,
        max_papers: int = settings.max_papers_per_run
    ) -> tuple[LiteratureBaseState, ObsidianVaultManager]:
        console.print(
            Panel(
                f"[bold cyan]Topic:[/bold cyan] {topic}\n"
                f"[bold yellow]Requirements:[/bold yellow] {requirements}\n"
                f"[bold green]Vault Target:[/bold green] {vault_path}\n"
                f"[bold magenta]Target Papers Goal:[/bold magenta] {max_papers}",
                title=f"🚀 [bold green]LitGraphAgent Initializing: '{base_id}'[/bold green]",
                border_style="cyan"
            )
        )

        vault = ObsidianVaultManager(vault_path)
        state = LiteratureBaseState(
            base_id=base_id,
            topic=topic,
            requirements=requirements,
            citation_format=citation_format,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat()
        )

        valid_candidates: list[Paper] = []
        seen_paper_ids: Set[str] = set()
        search_queries = [topic]
        search_round = 1
        max_rounds = 3

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=25, style="cyan", complete_style="green"),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
            refresh_per_second=4,
            transient=False,
        ) as progress:

            # =========================================================
            # STEP 1: Fast Adaptive Search & Pre-Filtered Validation
            # =========================================================
            search_task = progress.add_task(
                f"[yellow]🔍 Gathering verified papers (Goal: {max_papers})...",
                total=max_papers
            )

            while len(valid_candidates) < max_papers and search_round <= max_rounds and search_queries:
                curr_query = search_queries.pop(0)
                raw_candidates = self.search_engine.search_and_rank(curr_query, top_k=settings.max_search_candidates)

                # Pre-filter: validate only TOP-8 best heuristic candidates per round to save LLM time
                candidates_to_eval = [r for r in raw_candidates if r["id"] not in seen_paper_ids][:8]

                for raw in candidates_to_eval:
                    seen_paper_ids.add(raw["id"])
                    p = Paper(**raw)

                    # 1 Fast Consolidated LLM Call instead of 2
                    if self.validator.validate_candidate(p, topic, requirements):
                        compute_scientific_metrics(p)
                        valid_candidates.append(p)
                        progress.update(search_task, completed=min(len(valid_candidates), max_papers))

                        if len(valid_candidates) >= max_papers + 1:
                            break

                search_round += 1
                if len(valid_candidates) < max_papers and not search_queries and search_round <= max_rounds:
                    new_sub_queries = self._generate_sub_queries(topic, requirements, [topic])
                    search_queries.extend(new_sub_queries)

            progress.update(
                search_task,
                completed=min(len(valid_candidates), max_papers),
                description=f"[green]✓ Search complete: {len(valid_candidates)} papers verified"
            )

            if not valid_candidates:
                console.print("[red]❌ No papers passed validation.[/red]")
                return state, vault

            # =========================================================
            # STEP 2: Ranking & Elbow Cutoff
            # =========================================================
            valid_candidates.sort(key=lambda x: x.objective_scientific_score, reverse=True)
            scores = [p.objective_scientific_score for p in valid_candidates]

            min_floor = min(len(valid_candidates), settings.min_papers_per_run)
            max_ceiling = min(len(valid_candidates), max_papers)

            if settings.enable_elbow_cutoff and len(scores) > min_floor:
                cutoff_k = find_elbow_cutoff(scores, min_k=min_floor, max_k=max_ceiling)
            else:
                cutoff_k = max_ceiling

            selected_candidates = valid_candidates[:cutoff_k]
            for p in selected_candidates:
                p.is_elbow_selected = True

            # =========================================================
            # STEP 3: Synthesis & Knowledge Graph Ingestion
            # =========================================================
            synth_task = progress.add_task(
                f"[magenta]🧠 Ingesting {len(selected_candidates)} papers...",
                total=len(selected_candidates)
            )

            for p in selected_candidates:
                cit_data = self.search_engine.expand_citations(p.id, limit=settings.citation_expansion_limit)
                p.referenced_paper_titles = cit_data.get("references", [])
                p.citing_paper_titles = cit_data.get("citations", [])

                for ref in p.referenced_paper_titles:
                    state.edges.append(GraphEdge(source_title=p.title, target_title=ref, relation_type="cites"))
                for citing in p.citing_paper_titles:
                    state.edges.append(GraphEdge(source_title=citing, target_title=p.title, relation_type="cites"))

                self.synthesizer.synthesize_paper(p, citation_format)

                state.papers[p.id] = p
                for c in p.extracted_concepts:
                    state.concepts.add(c)

                progress.advance(synth_task)

            progress.update(synth_task, description=f"[green]✓ Ingested {len(selected_candidates)} papers")

            # =========================================================
            # STEP 4: Graph Links & Obsidian Flush
            # =========================================================
            master_task = progress.add_task("[blue]🕸️ Finalizing graph & Obsidian files...", total=3)

            self.synthesizer.link_paper_network(state)
            progress.advance(master_task)

            self.synthesizer.build_overall_synthesis(state)
            progress.advance(master_task)

            self.flush_to_vault(state, vault)
            progress.advance(master_task)

            progress.update(master_task, description="[green]✓ Vault ready")

        # Summary Table
        table = Table(title=f"📊 Selected Papers ({len(selected_candidates)} chosen)", border_style="magenta")
        table.add_column("#", justify="center")
        table.add_column("Title", style="white", max_width=45)
        table.add_column("Year", justify="center")
        table.add_column("Citations", justify="right", style="cyan")
        table.add_column("Score", justify="right", style="bold yellow")

        for i, p in enumerate(selected_candidates, 1):
            table.add_row(
                str(i),
                p.title,
                str(p.year or "N/A"),
                str(p.citation_count),
                f"{p.objective_scientific_score:.2f}"
            )
        console.print(table)

        console.print(
            Panel(
                f"[bold green]Vault Location:[/bold green] {vault_path}\n"
                f"[bold cyan]Total Verified Sources:[/bold cyan] {len(state.papers)}\n"
                f"[bold magenta]Connected Concepts:[/bold magenta] {len(state.concepts)}\n"
                f"[bold yellow]Graph Edges:[/bold yellow] {len(state.edges)}",
                title="✨ [bold green]Research Knowledge Graph Ready![/bold green]",
                border_style="green"
            )
        )
        return state, vault

    def update_base(
        self,
        state: LiteratureBaseState,
        vault: ObsidianVaultManager,
        directive_or_query: str,
        max_new_papers: int = settings.max_papers_per_run
    ) -> LiteratureBaseState:
        console.print(
            Panel(
                f"[bold yellow]Directive:[/bold yellow] {directive_or_query}\n"
                f"[bold cyan]Base:[/bold cyan] {state.base_id}",
                title="🔄 [bold yellow]Expanding Literature Base[/bold yellow]",
                border_style="yellow"
            )
        )
        state.updated_at = datetime.utcnow().isoformat()

        valid_candidates: list[Paper] = []
        seen_paper_ids = set(state.papers.keys())

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=25, style="cyan", complete_style="green"),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
            refresh_per_second=4,
            transient=False,
        ) as progress:

            search_task = progress.add_task(f"[yellow]🔍 Searching delta papers (Goal: {max_new_papers})...", total=max_new_papers)
            raw_candidates = self.search_engine.search_and_rank(directive_or_query, top_k=settings.max_search_candidates)
            candidates_to_eval = [r for r in raw_candidates if r["id"] not in seen_paper_ids][:8]

            for raw in candidates_to_eval:
                seen_paper_ids.add(raw["id"])
                p = Paper(**raw)

                if self.validator.validate_candidate(p, state.topic + " " + directive_or_query, state.requirements):
                    compute_scientific_metrics(p)
                    valid_candidates.append(p)
                    progress.update(search_task, completed=min(len(valid_candidates), max_new_papers))

                    if len(valid_candidates) >= max_new_papers:
                        break

            if not valid_candidates:
                console.print("[yellow]No new candidates satisfied criteria for this directive.[/yellow]")
                return state

            valid_candidates.sort(key=lambda x: x.objective_scientific_score, reverse=True)
            batch = valid_candidates[:max_new_papers]

            synth_task = progress.add_task(f"[magenta]🧠 Ingesting {len(batch)} delta papers...", total=len(batch))
            for p in batch:
                cit_data = self.search_engine.expand_citations(p.id, limit=settings.citation_expansion_limit)
                p.referenced_paper_titles = cit_data.get("references", [])
                p.citing_paper_titles = cit_data.get("citations", [])

                for ref in p.referenced_paper_titles:
                    state.edges.append(GraphEdge(source_title=p.title, target_title=ref, relation_type="cites"))

                self.synthesizer.synthesize_paper(p, state.citation_format)
                state.papers[p.id] = p
                for c in p.extracted_concepts:
                    state.concepts.add(c)
                progress.advance(synth_task)

            self.synthesizer.link_paper_network(state)
            self.synthesizer.build_overall_synthesis(state)
            self.flush_to_vault(state, vault)

        console.print(f"[bold green]✓ Base successfully updated with {len(batch)} new nodes![/bold green]")
        return state

    def flush_to_vault(self, state: LiteratureBaseState, vault: ObsidianVaultManager):
        for paper in state.papers.values():
            vault.write_paper_note(paper)
        for concept in state.concepts:
            linked_papers = [p.title for p in state.papers.values() if concept in p.extracted_concepts]
            vault.write_concept_note(concept, linked_papers)
        vault.write_hub_files(state)