from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.events import stream_run_events
from app.core.queue import enqueue_run
from app.core.states import transition_run
from app.models.evaluation import Evaluation
from app.models.run import Run
from app.models.step import Step
from app.models.task import Task
from app.schemas.runs import EvaluationRead, RunCreate, RunRead, StepRead

router = APIRouter(prefix="/api/runs", tags=["runs"])


RunStatusFilter = Literal["pending", "queued", "running", "evaluating", "success", "failed", "timeout", "cancelled"]


@router.post("", response_model=RunRead, status_code=status.HTTP_201_CREATED)
def create_run(payload: RunCreate, db: Session = Depends(get_db)) -> Run:
    task = db.scalar(select(Task).where(Task.task_key == payload.task_key))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    run = Run(
        task_id=task.id,
        status="pending",
        agent_mode=payload.agent_mode,
        model=payload.model,
        prompt_key=payload.prompt_key,
        runtime_key=payload.runtime_key,
        input=payload.input or task.spec.get("input"),
    )
    db.add(run)
    db.flush()
    transition_run(db, run, "queued")
    db.commit()
    db.refresh(run)
    try:
        enqueue_run(run.id)
    except Exception as exc:
        transition_run(db, run, "failed", error=str(exc), failure_type="QUEUE_ERROR")
        db.commit()
        raise HTTPException(status_code=503, detail="Failed to enqueue run") from exc
    return run


@router.get("", response_model=list[RunRead])
def list_runs(
    status: RunStatusFilter | None = Query(default=None),
    benchmark_run_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[Run]:
    stmt = select(Run).order_by(Run.created_at.desc())
    if status:
        stmt = stmt.where(Run.status == status)
    if benchmark_run_id:
        stmt = stmt.where(Run.benchmark_run_id == benchmark_run_id)
    return list(db.scalars(stmt).all())


@router.get("/{run_id}", response_model=RunRead)
def get_run(run_id: str, db: Session = Depends(get_db)) -> Run:
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/{run_id}/steps", response_model=list[StepRead])
def get_steps(run_id: str, db: Session = Depends(get_db)) -> list[Step]:
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return list(db.scalars(select(Step).where(Step.run_id == run_id).order_by(Step.step_index)).all())


@router.get("/{run_id}/evaluations", response_model=list[EvaluationRead])
def get_evaluations(run_id: str, db: Session = Depends(get_db)) -> list[Evaluation]:
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return list(db.scalars(select(Evaluation).where(Evaluation.run_id == run_id)).all())


@router.get("/{run_id}/events")
def get_events(run_id: str, after_id: int = 0) -> StreamingResponse:
    with SessionLocal() as db:
        run = db.get(Run, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
    return StreamingResponse(
        stream_run_events(SessionLocal, run_id, after_id=after_id),
        media_type="text/event-stream",
    )
