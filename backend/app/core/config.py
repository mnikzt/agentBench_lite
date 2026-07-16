from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AgentBench Lite"
    database_url: str = "postgresql+psycopg://agentbench:agentbench@localhost:5432/agentbench_lite"
    redis_url: str = "redis://localhost:6379/0"
    queue_name: str = "agentbench-runs"
    workspace_dir: Path = Path("./workspace")
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_use_json_response_format: bool = True
    default_llm_model: str = "gpt-4o-mini"
    judge_model: str = "gpt-4o-mini"
    model_cost_per_1k_tokens_usd: dict[str, float] = {"gpt-4o-mini": 0.0006}
    run_timeout_seconds: int = 120
    llm_request_timeout_seconds: float = 60
    allowed_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
