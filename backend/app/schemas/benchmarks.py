from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class BenchmarkRunCreate(BaseModel):
    task_set_key: str
    models: list[str] = Field(min_length=1)
    prompts: list[str] = Field(default_factory=lambda: ["baseline"])
    runtimes: list[Literal["react"]] = Field(default_factory=lambda: ["react"])
    repeat: int = Field(default=1, ge=1, le=20)


class BenchmarkRunRead(BaseModel):
    id: str
    task_set_id: str
    status: str
    config: dict
    summary: dict | None
    planned_runs: int
    completed_runs: int
    failed_runs: int
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class BenchmarkRunItemRead(BaseModel):
    id: str
    benchmark_run_id: str
    run_id: str
    task_id: str
    model: str
    prompt_key: str
    runtime_key: str
    repeat_index: int
    created_at: datetime

    model_config = {"from_attributes": True}
