from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.benchmark.matrix import expand_matrix
from app.benchmark.summarizer import summarize_benchmark
from app.core.database import get_db
from app.core.queue import enqueue_run
from app.core.states import transition_run
from app.models.benchmark import BenchmarkRun, BenchmarkRunItem
from app.models.run import Run
from app.models.task import new_uuid
from app.models.task_set import TaskSet, TaskSetItem
from app.schemas.benchmarks import BenchmarkRunCreate, BenchmarkRunItemRead, BenchmarkRunRead

router = APIRouter(prefix="/api/benchmarks", tags=["benchmarks"])


@router.post("/run", response_model=BenchmarkRunRead, status_code=status.HTTP_201_CREATED)
def create_benchmark_run(payload: BenchmarkRunCreate, db: Session = Depends(get_db)) -> BenchmarkRun:
    task_set = db.scalar(
        select(TaskSet)
        .where(TaskSet.task_set_key == payload.task_set_key)
        .options(selectinload(TaskSet.items).selectinload(TaskSetItem.task))
    )
    if not task_set:
        raise HTTPException(status_code=404, detail="Task set not found")
    tasks = [item.task for item in sorted(task_set.items, key=lambda item: item.sort_order)]
    if not tasks:
        raise HTTPException(status_code=400, detail="Task set has no tasks")

    cells = expand_matrix(tasks, payload.models, payload.prompts, payload.runtimes, payload.repeat)
    benchmark = BenchmarkRun(
        task_set_id=task_set.id,
        status="running",
        config=payload.model_dump(),
        planned_runs=len(cells),
        started_at=datetime.now(UTC),
    )
    db.add(benchmark)
    db.flush()

    run_ids: list[str] = []
    for cell in cells:
        run = Run(
            id=new_uuid(),
            task_id=cell.task.id,
            benchmark_run_id=benchmark.id,
            status="queued",
            agent_mode="react",
            model=cell.model,
            prompt_key=cell.prompt_key,
            runtime_key=cell.runtime_key,
            input=cell.task.spec.get("input"),
        )
        db.add(run)
        run_ids.append(run.id)
        db.add(
            BenchmarkRunItem(
                benchmark_run_id=benchmark.id,
                run_id=run.id,
                task_id=cell.task.id,
                model=cell.model,
                prompt_key=cell.prompt_key,
                runtime_key=cell.runtime_key,
                repeat_index=cell.repeat_index,
            )
        )

    db.commit()
    db.refresh(benchmark)
    enqueue_errors: list[str] = []
    for run_id in run_ids:
        try:
            enqueue_run(run_id)
        except Exception as exc:
            enqueue_errors.append(run_id)
            run = db.get(Run, run_id)
            if run:
                transition_run(db, run, "failed", error=str(exc), failure_type="QUEUE_ERROR")
    if enqueue_errors:
        benchmark.status = "failed"
        benchmark.failed_runs = len(enqueue_errors)
        db.add(benchmark)
        db.commit()
        db.refresh(benchmark)
    return benchmark


@router.get("", response_model=list[BenchmarkRunRead])
def list_benchmarks(db: Session = Depends(get_db)) -> list[BenchmarkRun]:
    return list(db.scalars(select(BenchmarkRun).order_by(BenchmarkRun.created_at.desc())).all())


@router.get("/{benchmark_run_id}", response_model=BenchmarkRunRead)
def get_benchmark(benchmark_run_id: str, db: Session = Depends(get_db)) -> BenchmarkRun:
    benchmark = db.get(BenchmarkRun, benchmark_run_id)
    if not benchmark:
        raise HTTPException(status_code=404, detail="Benchmark run not found")
    return benchmark


@router.get("/{benchmark_run_id}/items", response_model=list[BenchmarkRunItemRead])
def get_benchmark_items(
    benchmark_run_id: str,
    db: Session = Depends(get_db),
) -> list[BenchmarkRunItem]:
    benchmark = db.get(BenchmarkRun, benchmark_run_id)
    if not benchmark:
        raise HTTPException(status_code=404, detail="Benchmark run not found")
    return list(
        db.scalars(
            select(BenchmarkRunItem).where(BenchmarkRunItem.benchmark_run_id == benchmark_run_id)
        ).all()
    )


@router.post("/{benchmark_run_id}/summarize", response_model=BenchmarkRunRead)
def summarize(benchmark_run_id: str, db: Session = Depends(get_db)) -> BenchmarkRun:
    benchmark = db.get(BenchmarkRun, benchmark_run_id)
    if not benchmark:
        raise HTTPException(status_code=404, detail="Benchmark run not found")
    summarized = summarize_benchmark(db, benchmark_run_id)
    db.commit()
    db.refresh(summarized)
    return summarized
