import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Automatic discovery of the .env file in the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ROOT_ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_ENV_FILE if ROOT_ENV_FILE.exists() else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Universal LLM Configuration
    llm_api_key: str = Field(default="sk-placeholder")
    llm_base_url: str = Field(default="https://api.openai.com/v1")
    llm_model: str = Field(default="gpt-4o")
    llm_timeout: float = Field(default=90.0)
    llm_max_retries: int = Field(default=3)
    llm_cache_enabled: bool = Field(default=False)

    # Academic Search API
    semantic_scholar_api_key: str | None = None
    http_timeout: float = Field(default=15.0)
    http_max_retries: int = Field(default=3)

    # Network cache (search results / citation expansion)
    cache_enabled: bool = Field(default=True)
    cache_dir: Path = Field(default=Path(".litgraph_cache"))
    cache_ttl_hours: int = Field(default=168)

    # Vault storage
    default_vaults_dir: Path = Field(default=Path("./vaults"))

    # Pipeline Thresholds
    max_papers_per_run: int = 5
    min_papers_per_run: int = 2
    max_search_candidates: int = 15
    candidate_eval_limit: int = 8
    citation_expansion_limit: int = 2
    enable_elbow_cutoff: bool = True

    # Dynamic search-engine routing (LLM picks engines from the tool catalog)
    search_router_enabled: bool = True
    search_router_max_primary: int = 2
    search_fallback_min_results: int = 5
    search_engines_override: str = ""

    # Knowledge-graph quality controls
    min_concept_papers: int = 2
    max_concepts_per_paper: int = 8
    concept_batch_size: int = 12
    bibliography_batch_size: int = 20

    def model_post_init(self, __context):
        if self.llm_api_key == "sk-placeholder":
            for key in [
                "LLM_API_KEY",
                "OPENROUTER_API_KEY",
                "DEEPSEEK_API_KEY",
                "OPENAI_API_KEY",
                "GROQ_API_KEY",
            ]:
                if os.getenv(key):
                    self.llm_api_key = os.environ[key]
                    break

        # Relative paths are resolved against the project root, not the CWD,
        # so vaults and caches never land in an unexpected directory.
        if not self.default_vaults_dir.is_absolute():
            self.default_vaults_dir = (PROJECT_ROOT / self.default_vaults_dir).resolve()
        if not self.cache_dir.is_absolute():
            self.cache_dir = (PROJECT_ROOT / self.cache_dir).resolve()


settings = Settings()
