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
from ..models import Paper, LiteratureBaseState, GraphEdge, ConceptHub
from ..search.engine import AcademicSearchEngine
from ..search.pdf_extractor import EphemeralPDFReader
from ..search.ranking import compute_scientific_metrics, find_elbow_cutoff
from .validator import LiteratureValidator
from .synthesizer import LiteratureSynthesizer
from ..storage.obsidian_vault import ObsidianVaultManager

console = Console(force_terminal=True)


class LiteratureAgent:
    """Fast Optimized Research Agent with Batch Concept Synthesis and Optional Deep PDF Mode."""

    def __init__(self, llm: BaseLLMProvider, search_engine: AcademicSearchEngine):
        self.llm = llm
        self.search_engine = search_engine
        self.validator = LiteratureValidator(llm)
        self.synthesizer = LiteratureSynthesizer(llm)
        self.pdf_reader = EphemeralPDFReader()

    def _calculate_continuous_weights(self, state: LiteratureBaseState, selected_papers: List[Paper]):
        if not selected_papers:
            return

        scores = [p.objective_scientific_score for p in selected_papers]
        max_s = max(scores) if scores else 1.0
        min_s = min(scores) if scores else 0.0

        for p in selected_papers:
            norm = (p.objective_scientific_score - min_s) / (max_s - min_s) if max_s > min_s else 1.0
            p.normalized_weight = round(0.2 + (0.8 * norm), 3)

        concept_to_papers: dict[str, list[Paper]] = {}
        for p in selected_papers:
            for c in p.extracted_concepts:
                c_clean = c.strip()
                if c_clean:
                    matched_key = next((k for k in concept_to_papers if k.lower() == c_clean.lower()), c_clean)
                    concept_to_papers.setdefault(matched_key, []).append(p)

        concept_raw_scores = {c_name: sum(p.objective_scientific_score for p in papers) for c_name, papers in concept_to_papers.items()}
        max_c = max(concept_raw_scores.values()) if concept_raw_scores else 1.0
        min_c = min(concept_raw_scores.values()) if concept_raw_scores else 0.0

        state.concepts.clear()
        for c_name, raw_score in concept_raw_scores.items():
            norm_c = (raw_score - min_c) / (max_c - min_c) if max_c > min_c else 1.0
            state.concepts[c_name] = ConceptHub(
                name=c_name,
                aggregated_score=round(raw_score, 2),
                normalized_weight=round(0.2 + (0.8 * norm_c), 3)
            )

    def initialize_base(
        self,
        base_id: str,
        topic: str,
        requirements: str,
        citation_format: str,
        vault_path: str,
        max_papers: int = settings.max_papers_per_run,
        deep_scan: bool = False
    ) -> tuple[LiteratureBaseState, ObsidianVaultManager]:
        mode_label = "[bold red]DEEP PDF MODE[/bold red]" if deep_scan else "[bold green]FAST MODE (Abstract-based)[/bold green]"
        console.print(
            Panel(
                f"[bold cyan]Topic:[/bold cyan] {topic}\n"
                f"[bold yellow]Requirements:[/bold yellow] {requirements}\n"
                f"[bold green]Vault Target:[/bold green] {vault_path}\n"
                f"[bold magenta]Target Papers Goal:[/bold magenta] {max_papers} | [bold blue]Mode:[/bold blue] {mode_label}",
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

            # STEP 1: Search & Pre-filtered Validation (1 call per paper)
            search_task = progress.add_task(f"[yellow]🔍 Gathering papers (Goal: {max_papers})...", total=max_papers)
            while len(valid_candidates) < max_papers and search_round <= max_rounds and search_queries:
                curr_query = search_queries.pop(0)
                raw_candidates = self.search_engine.search_and_rank(curr_query, top_k=settings.max_search_candidates)
                candidates_to_eval = [r for r in raw_candidates if r["id"] not in seen_paper_ids][:8]

                for raw in candidates_to_eval:
                    seen_paper_ids.add(raw["id"])
                    p = Paper(**raw)
                    if self.validator.validate_candidate(p, topic, requirements):
                        compute_scientific_metrics(p)
                        valid_candidates.append(p)
                        progress.update(search_task, completed=min(len(valid_candidates), max_papers))
                        if len(valid_candidates) >= max_papers + 1:
                            break

                search_round += 1

            if not valid_candidates:
                console.print("[red]❌ No papers passed validation.[/red]")
                return state, vault

            # STEP 2: Ranking & Cutoff
            valid_candidates.sort(key=lambda x: x.objective_scientific_score, reverse=True)
            scores = [p.objective_scientific_score for p in valid_candidates]
            cutoff_k = find_elbow_cutoff(scores, min_k=min(len(scores), settings.min_papers_per_run), max_k=max_papers)
            selected_candidates = valid_candidates[:cutoff_k]

            # STEP 3: Paper Content Synthesis (Fast Abstract-Based Ingestion)
            synth_task = progress.add_task(f"[magenta]🧠 Ingesting {len(selected_candidates)} papers...", total=len(selected_candidates))
            for p in selected_candidates:
                cit_data = self.search_engine.expand_citations(p.id, limit=settings.citation_expansion_limit)
                p.referenced_paper_titles = cit_data.get("references", [])
                p.citing_paper_titles = cit_data.get("citations", [])

                for ref in p.referenced_paper_titles:
                    state.edges.append(GraphEdge(source_title=p.title, target_title=ref, relation_type="cites"))

                # 1 fast LLM call extracts summary + concepts from abstract
                self.synthesizer.synthesize_paper_content(p)

                # Optional Deep PDF scan only if explicitly enabled
                if deep_scan:
                    pages_dict = self.pdf_reader.fetch_pages(p.doi_or_url or "")
                    if pages_dict:
                        self.synthesizer.ground_concepts_to_pages(p, pages_dict)
                        del pages_dict

                state.papers[p.id] = p
                progress.advance(synth_task)

            # Calculate continuous weights
            self._calculate_continuous_weights(state, selected_candidates)

            # STEP 4: Batch Concept Synthesis & Master Files (Only 3 fast calls total!)
            master_task = progress.add_task("[blue]🕸️ Synthesizing concept hubs & bibliography...", total=4)

            # 1 single consolidated batch call for ALL concepts
            self.synthesizer.synthesize_all_concept_hubs_batch(state)
            progress.advance(master_task)

            # 1 single unified batch call for bibliography
            self.synthesizer.harmonize_master_bibliography(state)
            progress.advance(master_task)

            self.synthesizer.link_paper_network(state)
            progress.advance(master_task)

            self.synthesizer.build_overall_synthesis(state)
            self.flush_to_vault(state, vault)
            progress.advance(master_task)

        # Output Summary Table
        table = Table(title=f"📊 Selected Papers ({len(selected_candidates)} chosen)", border_style="magenta")
        table.add_column("Rank", justify="center")
        table.add_column("Title", style="white", max_width=45)
        table.add_column("Citations", justify="right", style="cyan")
        table.add_column("Score", justify="right", style="bold yellow")
        table.add_column("Weight (0-1)", justify="right", style="green")

        for i, p in enumerate(selected_candidates, 1):
            table.add_row(str(i), p.title, str(p.citation_count), f"{p.objective_scientific_score:.2f}", f"{p.normalized_weight:.3f}")
        console.print(table)

        console.print(
            Panel(
                f"[bold green]Vault Location:[/bold green] {vault_path}\n"
                f"[bold cyan]Total Verified Sources:[/bold cyan] {len(state.papers)}\n"
                f"[bold magenta]Full Concept Hubs Created:[/bold magenta] {len(state.concepts)}\n"
                f"[bold yellow]Graph Connections:[/bold yellow] {len(state.edges)}",
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
        max_new_papers: int = settings.max_papers_per_run,
        deep_scan: bool = False
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

        raw_candidates = self.search_engine.search_and_rank(directive_or_query, top_k=settings.max_search_candidates)
        candidates_to_eval = [r for r in raw_candidates if r["id"] not in seen_paper_ids][:8]

        for raw in candidates_to_eval:
            seen_paper_ids.add(raw["id"])
            p = Paper(**raw)
            if self.validator.validate_candidate(p, state.topic + " " + directive_or_query, state.requirements):
                compute_scientific_metrics(p)
                valid_candidates.append(p)
                if len(valid_candidates) >= max_new_papers:
                    break

        if not valid_candidates:
            console.print("[yellow]No new candidates satisfied criteria.[/yellow]")
            return state

        batch = valid_candidates[:max_new_papers]
        for p in batch:
            cit_data = self.search_engine.expand_citations(p.id, limit=settings.citation_expansion_limit)
            p.referenced_paper_titles = cit_data.get("references", [])
            p.citing_paper_titles = cit_data.get("citations", [])

            self.synthesizer.synthesize_paper_content(p)
            if deep_scan:
                pages_dict = self.pdf_reader.fetch_pages(p.doi_or_url or "")
                if pages_dict:
                    self.synthesizer.ground_concepts_to_pages(p, pages_dict)
                    del pages_dict

            state.papers[p.id] = p

        self._calculate_continuous_weights(state, list(state.papers.values()))
        self.synthesizer.synthesize_all_concept_hubs_batch(state)
        self.synthesizer.harmonize_master_bibliography(state)
        self.synthesizer.link_paper_network(state)
        self.synthesizer.build_overall_synthesis(state)
        self.flush_to_vault(state, vault)

        console.print(f"[bold green]✓ Base successfully updated with {len(batch)} new nodes![/bold green]")
        return state

    def flush_to_vault(self, state: LiteratureBaseState, vault: ObsidianVaultManager):
        for paper in state.papers.values():
            vault.write_paper_note(paper)
        for concept_name, hub in state.concepts.items():
            vault.write_concept_note(hub, state)
        vault.write_hub_files(state)