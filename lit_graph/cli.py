import argparse
from .config import settings
from .llm.providers import UniversalLLMProvider
from .search.engine import AcademicSearchEngine
from .agent.core import LiteratureAgent
from .storage.base_manager import LiteratureManager


def main():
    parser = argparse.ArgumentParser(
        description="LitGraphAgent: Autonomous Literature Research & Knowledge Graph Builder for Obsidian"
    )
    parser.add_argument("--id", type=str, default="knowledge_base_01", help="Unique ID / directory name for the vault")
    parser.add_argument("--topic", type=str, required=True, help="Research topic")
    parser.add_argument("--requirements", type=str, default="High quality, rigorous methodology, recent sources", help="Filtering criteria")
    parser.add_argument("--format", type=str, default="APA 7th", help="Citation format (APA 7th, BibTeX, IEEE, Harvard)")
    parser.add_argument("--update", type=str, default=None, help="Incremental directive to expand existing base")
    parser.add_argument("--max-papers", type=int, default=settings.max_papers_per_run, help="Max papers to add in this run")
    parser.add_argument("--deep", action="store_true", help="Enable multi-page PDF scanning and page citations (slower on CPU)")
    args = parser.parse_args()

    # 1. Initialize Universal LLM Provider
    llm = UniversalLLMProvider(
        api_key=settings.llm_api_key,
        model_name=settings.llm_model,
        base_url=settings.llm_base_url
    )

    # 2. Initialize Core Agent
    searcher = AcademicSearchEngine(s2_api_key=settings.semantic_scholar_api_key)
    agent = LiteratureAgent(llm=llm, search_engine=searcher)
    manager = LiteratureManager(root_vaults_dir=settings.default_vaults_dir, agent=agent)

    # 3. Execution
    if args.update:
        manager.update_base(
            base_id=args.id,
            directive=args.update,
            max_new_papers=args.max_papers,
            deep_scan=args.deep
        )
    else:
        manager.create_base(
            base_id=args.id,
            topic=args.topic,
            requirements=args.requirements,
            citation_format=args.format,
            max_papers=args.max_papers,
            deep_scan=args.deep
        )


if __name__ == "__main__":
    main()