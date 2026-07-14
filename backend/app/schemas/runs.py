from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class RunCreate(BaseModel):
    task_key: str
    input: dict | None = None
    agent_mode: Literal["react"] = "react"
    model: str
    prompt_key: str | None = "baseline"
    runtime_key: Literal["react"] = "react"


class RunRead(BaseModel):
    id: str
    task_id: str
    benchmark_run_id: str | None = None
    status: str
    agent_mode: str
    model: str
    prompt_key: str | None
    runtime_key: str
    input: dict | None
    final_output: dict | None
    error: str | None
    failure_type: str | None
    score: Decimal | None
    passed: bool | None
    total_steps: int
    total_latency_ms: int
    total_tokens: int
    total_cost_usd: Decimal
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StepRead(BaseModel):
    id: str
    run_id: str
    step_index: int
    phase: str | None
    thought: str | None
    action: str | None
    tool_name: str | None
    tool_input: dict | None
    tool_output: dict | None
    observation: str | None
    error: str | None
    failure_type: str | None
    latency_ms: int | None
    tokens: int
    cost_usd: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}


class EvaluationRead(BaseModel):
    id: str
    run_id: str
    evaluator_type: str
    score: Decimal | None
    passed: bool | None
    details: dict | None
    error: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
