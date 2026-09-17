import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Автоматический поиск .env в корне проекта LitGraphAgent
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ROOT_ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_ENV_FILE if ROOT_ENV_FILE.exists() else ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Universal LLM Configuration
    llm_api_key: str = Field(default="sk-placeholder")
    llm_base_url: str = Field(default="https://api.openai.com/v1")
    llm_model: str = Field(default="gpt-4o")

    # Academic Search API
    semantic_scholar_api_key: str | None = None
    default_vaults_dir: Path = Path("./vaults")

    # Pipeline Thresholds
    max_papers_per_run: int = 5
    min_papers_per_run: int = 2
    max_search_candidates: int = 15
    citation_expansion_limit: int = 2
    enable_elbow_cutoff: bool = True

    def model_post_init(self, __context):
        if self.llm_api_key == "sk-placeholder":
            for key in ["LLM_API_KEY", "OPENROUTER_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY"]:
                if os.getenv(key):
                    self.llm_api_key = os.environ[key]
                    break


settings = Settings()