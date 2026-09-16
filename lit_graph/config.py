import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Universal LLM parameters (configured for DeepSeek by default)
    llm_api_key: str = Field(default="sk-placeholder")
    llm_base_url: str = Field(default="https://api.deepseek.com")
    llm_model: str = Field(default="deepseek-chat")

    # Academic Search API
    semantic_scholar_api_key: str | None = None
    default_vaults_dir: Path = Path("./vaults")

    # Pipeline & Scientific Ranking Limits
    max_papers_per_run: int = 8
    min_papers_per_run: int = 3
    max_search_candidates: int = 25
    citation_expansion_limit: int = 3
    enable_elbow_cutoff: bool = True

    def model_post_init(self, __context):
        if self.llm_api_key == "sk-placeholder":
            for key in ["DEEPSEEK_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY"]:
                if os.getenv(key):
                    self.llm_api_key = os.environ[key]
                    break


settings = Settings()