import argparse
import logging
import sys

from rich.console import Console
from rich.table import Table
from rich.text import Text

from . import __version__
from .agent.core import LiteratureAgent
from .agent.roles import TEAM_ORDER, get_role
from .config import settings
from .llm.providers import UniversalLLMProvider
from .qa.vault_checks import run_state_checks, run_vault_checks
from .search.engine import AcademicSearchEngine
from .storage.base_manager import LiteratureManager
from .storage.obsidian_vault import ObsidianVaultManager
from .utils.logging_setup import configure_logging

console = Console()


def _force_utf8() -> None:
    """Windows consoles default to cp1251/cp866 and crash on emoji output."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="litgraph",
        description="LitGraphAgent: Autonomous Literature Research & Knowledge Graph Builder for Obsidian",
    )
    parser.add_argument("--id", type=str, default="knowledge_base_01", help="Unique ID / directory name for the vault")
    parser.add_argument("--topic", type=str, default=None, help="Research topic (required when creating a base)")
    parser.add_argument(
        "--requirements",
        type=str,
        default="High quality, rigorous methodology, recent sources",
        help="Filtering criteria",
    )
    parser.add_argument(
        "--format",
        type=str,
        default="APA 7th",
        help="Citation format (APA 7th, BibTeX, IEEE, Harvard, GOST)",
    )
    parser.add_argument("--update", type=str, default=None, help="Incremental directive to expand an existing base")
    parser.add_argument(
        "--max-papers",
        type=int,
        default=settings.max_papers_per_run,
        help="Max papers to add in this run",
    )
    parser.add_argument(
        "--deep",
        action="store_true",
        help="Enable multi-page PDF scanning and page citations (slower on CPU)",
    )
    parser.add_argument("--list", action="store_true", help="List existing literature bases and exit")
    parser.add_argument("--delete", action="store_true", help="Delete the base identified by --id and exit")
    parser.add_argument("--check", action="store_true", help="Run QA checks on the vault identified by --id")
    parser.add_argument("--team", action="store_true", help="Show the agent team and role ownership")
    parser.add_argument("--no-cache", action="store_true", help="Disable the on-disk search cache")
    parser.add_argument("--no-elbow", action="store_true", help="Disable elbow cutoff (keep top max-papers)")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("--version", action="version", version=f"litgraph-agent {__version__}")
    return parser


def _print_team() -> None:
    table = Table(title="🤖 LitGraphAgent Team & Agent Ownership", border_style="cyan")
    table.add_column("Role", style="bold")
    table.add_column("Owner")
    table.add_column("Agent", style="green")
    table.add_column("Responsibility", style="white")
    for key in TEAM_ORDER:
        role = get_role(key)
        table.add_row(role.title, f"{role.owner} ({role.handle})", role.agent, Text(role.responsibility))
    console.print(table)


def _print_issues(issues: list) -> None:
    table = Table(title="QA Report", border_style="yellow")
    table.add_column("Severity")
    table.add_column("Code", style="cyan")
    table.add_column("Message", style="white", max_width=70)
    table.add_column("Path", style="dim")
    for issue in issues:
        colour = {"error": "red", "warning": "yellow", "info": "blue"}.get(issue.severity, "white")
        table.add_row(f"[{colour}]{issue.severity}[/{colour}]", issue.code, issue.message, issue.path)
    console.print(table)


def _run_check(base_id: str) -> int:
    vault_path = settings.default_vaults_dir / base_id
    if not vault_path.exists():
        console.print(f"[red]Vault not found: {vault_path}[/red]")
        return 1

    report = run_vault_checks(vault_path)
    vault = ObsidianVaultManager(vault_path)
    state = vault.load_state(base_id)
    if state is not None:
        report.merge(run_state_checks(state))

    console.print(f"[bold]Vault:[/bold] {vault_path}")
    console.print(f"[bold]Summary:[/bold] {report.summary()}")
    if report.issues:
        _print_issues(report.issues)
    return 1 if report.errors else 0


def main(argv: list[str] | None = None) -> int:
    _force_utf8()
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    if args.no_cache:
        settings.cache_enabled = False
    if args.no_elbow:
        settings.enable_elbow_cutoff = False
    if args.max_papers < 1:
        parser.error("--max-papers must be at least 1")

    try:
        if args.team:
            _print_team()
            return 0

        if args.check:
            return _run_check(args.id)

        if args.list:
            manager = LiteratureManager(root_vaults_dir=settings.default_vaults_dir)
            bases = manager.list_bases()
            if not bases:
                console.print("[yellow]No literature bases found.[/yellow]")
            for base_id in bases:
                console.print(f"- {base_id}")
            return 0

        if args.delete:
            manager = LiteratureManager(root_vaults_dir=settings.default_vaults_dir)
            manager.delete_base(args.id)
            console.print(f"[green]Deleted base '{args.id}'.[/green]")
            return 0

        llm = UniversalLLMProvider(
            api_key=settings.llm_api_key,
            model_name=settings.llm_model,
            base_url=settings.llm_base_url,
        )
        searcher = AcademicSearchEngine(s2_api_key=settings.semantic_scholar_api_key)
        agent = LiteratureAgent(llm=llm, search_engine=searcher)
        manager = LiteratureManager(root_vaults_dir=settings.default_vaults_dir, agent=agent)

        if args.update:
            result = manager.update_base(
                base_id=args.id,
                directive=args.update,
                max_new_papers=args.max_papers,
                deep_scan=args.deep,
            )
            if result is None:
                console.print("[red]Update failed: base not found or invalid.[/red]")
                return 1
            return 0

        if not args.topic:
            parser.error("--topic is required when creating a new base")

        result = manager.create_base(
            base_id=args.id,
            topic=args.topic,
            requirements=args.requirements,
            citation_format=args.format,
            max_papers=args.max_papers,
            deep_scan=args.deep,
        )
        if result is None:
            console.print(f"[red]Base '{args.id}' already exists. Use --update to extend it.[/red]")
            return 1
        return 0
    except KeyboardInterrupt:
        console.print("[yellow]Interrupted.[/yellow]")
        return 130
    except Exception as exc:  # noqa: BLE001 - top-level CLI guard
        logging.getLogger("lit_graph.cli").exception("Unhandled error: %s", exc)
        console.print(f"[red]Error: {exc}[/red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
