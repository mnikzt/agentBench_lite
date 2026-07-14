import asyncio
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.benchmark.summarizer import summarize_benchmark
from app.core.database import SessionLocal
from app.core.events import record_event
from app.core.states import InvalidStateTransition, TERMINAL_RUN_STATUSES, transition_run
from app.evaluator.pipeline import EvaluatorPipeline
from app.models.benchmark import BenchmarkRunItem
from app.models.run import Run
from app.models.step import Step
from app.runtime.llm_client import build_llm_client
from app.runtime.react import ReActRuntime


def execute_run_job(run_id: str) -> None:
    asyncio.run(_execute_run_with_timeout(run_id))


async def _execute_run_with_timeout(run_id: str) -> None:
    try:
        await asyncio.wait_for(_execute_run(run_id), timeout=get_settings().run_timeout_seconds)
    except asyncio.TimeoutError:
        with SessionLocal() as db:
            run = db.get(Run, run_id)
            if run and run.status not in TERMINAL_RUN_STATUSES:
                _record_failed_step_if_needed(db, run, "Run timed out", "TIMEOUT")
                transition_run(db, run, "timeout", error="Run timed out", failure_type="TIMEOUT")
                record_event(
                    db,
                    run.id,
                    "run_failed",
                    {"run_id": run.id, "error": "Run timed out", "failure_type": "TIMEOUT"},
                )
                db.commit()
        _summarize_parent_if_terminal(run_id)


async def _execute_run(run_id: str) -> None:
    with SessionLocal() as db:
        run = db.get(Run, run_id)
        if not run:
            raise ValueError(f"Run not found: {run_id}")
        if run.status != "queued":
            return

        try:
            transition_run(db, run, "running")
            db.commit()
            db.refresh(run)

            task_spec = run.task.spec
            runtime = ReActRuntime(db, build_llm_client(run.model))
            await runtime.run(run.id, task_spec, run.input)
            db.refresh(run)

            transition_run(db, run, "evaluating")
            db.commit()
            await EvaluatorPipeline(db).evaluate(run, task_spec)
            transition_run(db, run, "success")
            db.commit()
        except InvalidStateTransition:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            run = db.get(Run, run_id)
            if run:
                failure_type = _classify_failure(exc)
                _record_failed_step_if_needed(db, run, str(exc), failure_type)
                _update_run_totals(db, run)
                status = "timeout" if failure_type == "TIMEOUT" else "failed"
                try:
                    transition_run(db, run, status, error=str(exc), failure_type=failure_type)
                except InvalidStateTransition:
                    run.status = status
                    run.error = str(exc)
                    run.failure_type = failure_type
                    run.finished_at = datetime.now(UTC)
                record_event(
                    db,
                    run.id,
                    "run_failed",
                    {"run_id": run.id, "error": str(exc), "failure_type": failure_type},
                )
                db.add(run)
                db.commit()
        finally:
            _summarize_parent_if_terminal(run_id)


def _summarize_parent_if_terminal(run_id: str) -> None:
    with SessionLocal() as db:
        run = db.get(Run, run_id)
        if not run or run.status not in TERMINAL_RUN_STATUSES:
            return
        item = db.scalar(select(BenchmarkRunItem).where(BenchmarkRunItem.run_id == run_id))
        if not item:
            return
        summarize_benchmark(db, item.benchmark_run_id)
        db.commit()


def _record_failed_step_if_needed(db: Session, run: Run, error: str, failure_type: str) -> None:
    existing_steps = list(
        db.scalars(select(Step).where(Step.run_id == run.id).order_by(Step.step_index)).all()
    )
    if existing_steps and existing_steps[-1].error:
        return
    step_index = existing_steps[-1].step_index + 1 if existing_steps else 0
    db.add(
        Step(
            run_id=run.id,
            step_index=step_index,
            phase="failed",
            action="failed",
            observation=error,
            error=error,
            failure_type=failure_type,
            latency_ms=0,
        )
    )
    db.flush()


def _update_run_totals(db: Session, run: Run) -> None:
    steps = list(db.scalars(select(Step).where(Step.run_id == run.id)).all())
    run.total_steps = len(steps)
    run.total_latency_ms = sum(step.latency_ms or 0 for step in steps)
    run.total_tokens = sum(step.tokens for step in steps)
    run.total_cost_usd = sum((step.cost_usd for step in steps), Decimal("0"))


def _classify_failure(error: Exception) -> str:
    if isinstance(error, TimeoutError):
        return "TIMEOUT"
    upper = str(error).upper()
    if "MAX_STEPS" in upper:
        return "MAX_STEPS_EXCEEDED"
    if "TIMEOUT" in upper:
        return "TIMEOUT"
    if "SCHEMA" in upper or "VALIDATION" in upper:
        return "OUTPUT_SCHEMA_ERROR"
    if "HTTP" in upper or "BROWSER" in upper or "TOOL" in upper:
        return "TOOL_ERROR"
    if "LLM" in upper or "OPENAI" in upper:
        return "LLM_ERROR"
    return "UNKNOWN"
