from collections.abc import Generator

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.benchmarks import create_benchmark_run
from app.api.runs import create_run
from app.core.database import Base
from app.models.benchmark import BenchmarkRunItem
from app.models.run import Run
from app.models.task import Task
from app.models.task_set import TaskSet, TaskSetItem
from app.schemas.benchmarks import BenchmarkRunCreate
from app.schemas.runs import RunCreate


@pytest.fixture
def db(tmp_path) -> Generator[Session, None, None]:
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_create_run_queues_run_without_executing_inline(db: Session, monkeypatch):
    enqueued: list[str] = []
    monkeypatch.setattr("app.api.runs.enqueue_run", enqueued.append)
    task = Task(task_key="extract_price_demo", name="Extract Price", spec={"input": {"url": "x"}})
    db.add(task)
    db.commit()

    run = create_run(
        RunCreate(task_key="extract_price_demo", model="gpt-4o-mini", input={"url": "x"}),
        db=db,
    )

    assert run.status == "queued"
    assert run.started_at is None
    assert run.finished_at is None
    assert db.scalar(select(Run).where(Run.id == run.id)).status == "queued"
    assert enqueued == [run.id]


def test_create_run_marks_failed_when_enqueue_fails(db: Session, monkeypatch):
    def fail_enqueue(run_id: str) -> None:
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr("app.api.runs.enqueue_run", fail_enqueue)
    task = Task(task_key="extract_price_demo", name="Extract Price", spec={"input": {"url": "x"}})
    db.add(task)
    db.commit()

    with pytest.raises(HTTPException) as exc:
        create_run(
            RunCreate(task_key="extract_price_demo", model="gpt-4o-mini", input={"url": "x"}),
            db=db,
        )

    run = db.scalar(select(Run))
    assert exc.value.status_code == 503
    assert run.status == "failed"
    assert run.failure_type == "QUEUE_ERROR"


def test_create_benchmark_expands_and_queues_matrix_runs(db: Session, monkeypatch):
    enqueued: list[str] = []
    monkeypatch.setattr("app.api.benchmarks.enqueue_run", enqueued.append)
    task = Task(task_key="extract_price_demo", name="Extract Price", spec={"input": {"url": "x"}})
    task_set = TaskSet(task_set_key="web_basic", name="Web Basic")
    db.add_all([task, task_set])
    db.flush()
    db.add(TaskSetItem(task_set_id=task_set.id, task_id=task.id, sort_order=0))
    db.commit()

    benchmark = create_benchmark_run(
        BenchmarkRunCreate(
            task_set_key="web_basic",
            models=["gpt-4o-mini"],
            prompts=["baseline", "tool_first"],
            runtimes=["react"],
            repeat=2,
        ),
        db=db,
    )

    runs = db.scalars(select(Run).where(Run.benchmark_run_id == benchmark.id)).all()
    items = db.scalars(
        select(BenchmarkRunItem).where(BenchmarkRunItem.benchmark_run_id == benchmark.id)
    ).all()
    assert benchmark.status == "running"
    assert benchmark.started_at is not None
    assert benchmark.planned_runs == 4
    assert len(runs) == 4
    assert len(items) == 4
    assert {run.status for run in runs} == {"queued"}
    assert {run.model for run in runs} == {"gpt-4o-mini"}
    assert {run.prompt_key for run in runs} == {"baseline", "tool_first"}
    assert {run.runtime_key for run in runs} == {"react"}
    assert {item.repeat_index for item in items} == {0, 1}
    assert sorted(enqueued) == sorted(run.id for run in runs)


def test_create_benchmark_marks_failed_runs_when_partial_enqueue_fails(db: Session, monkeypatch):
    calls = 0

    def partially_fail_enqueue(run_id: str) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("redis unavailable")

    monkeypatch.setattr("app.api.benchmarks.enqueue_run", partially_fail_enqueue)
    task = Task(task_key="extract_price_demo", name="Extract Price", spec={"input": {"url": "x"}})
    task_set = TaskSet(task_set_key="web_basic", name="Web Basic")
    db.add_all([task, task_set])
    db.flush()
    db.add(TaskSetItem(task_set_id=task_set.id, task_id=task.id, sort_order=0))
    db.commit()

    benchmark = create_benchmark_run(
        BenchmarkRunCreate(
            task_set_key="web_basic",
            models=["gpt-4o-mini"],
            prompts=["baseline"],
            runtimes=["react"],
            repeat=2,
        ),
        db=db,
    )

    runs = db.scalars(select(Run).where(Run.benchmark_run_id == benchmark.id)).all()
    assert benchmark.status == "failed"
    assert benchmark.failed_runs == 1
    assert sorted(run.status for run in runs) == ["failed", "queued"]
    failed_run = next(run for run in runs if run.status == "failed")
    assert failed_run.failure_type == "QUEUE_ERROR"
