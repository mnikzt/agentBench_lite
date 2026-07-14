import asyncio
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.models.evaluation import Evaluation
from app.models.run import Run, RunEvent
from app.models.step import Step
from app.models.task import Task
from app.worker import runner


@pytest.fixture
def session_factory(tmp_path) -> Generator[sessionmaker[Session], None, None]:
    engine = create_engine(f"sqlite:///{tmp_path / 'worker.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    try:
        yield factory
    finally:
        Base.metadata.drop_all(bind=engine)


def test_worker_executes_queued_run_with_mock_llm(session_factory, monkeypatch):
    monkeypatch.setattr(runner, "SessionLocal", session_factory)
    task_spec = {
        "input": {"file_path": "demo_files/sample_page.txt"},
        "agent": {"max_steps": 3, "timeout_seconds": 10},
        "tools": ["file"],
        "expected_output": {
            "schema": {
                "type": "object",
                "required": ["summary"],
                "properties": {"summary": {"type": "string"}},
            }
        },
        "evaluation": [
            {"type": "json_schema"},
            {"type": "llm_judge", "rubric": "Final output should exist."},
        ],
    }
    with session_factory() as db:
        task = Task(task_key="file_read_demo_001", name="File Demo", spec=task_spec)
        db.add(task)
        db.flush()
        run = Run(task_id=task.id, status="queued", model="mock", input=task_spec["input"])
        db.add(run)
        db.commit()
        run_id = run.id

    asyncio.run(runner._execute_run(run_id))

    with session_factory() as db:
        run = db.get(Run, run_id)
        steps = db.scalars(select(Step).where(Step.run_id == run_id).order_by(Step.step_index)).all()
        evaluations = db.scalars(select(Evaluation).where(Evaluation.run_id == run_id)).all()
        events = db.scalars(select(RunEvent).where(RunEvent.run_id == run_id).order_by(RunEvent.id)).all()

    assert run.status == "success"
    assert run.failure_type is None
    assert run.final_output["summary"].startswith("Read ")
    assert len(steps) == 2
    assert steps[0].tool_name == "file"
    assert steps[1].action == "final"
    assert len(evaluations) == 2
    assert {evaluation.evaluator_type for evaluation in evaluations} == {"json_schema", "llm_judge"}
    assert all(evaluation.passed for evaluation in evaluations)
    assert run.score is not None
    assert run.total_steps == 2
    assert run.total_latency_ms >= 0
    assert {
        "run_started",
        "step_started",
        "tool_called",
        "tool_result",
        "run_finished",
        "evaluation_finished",
    }.issubset({event.event_type for event in events})


def test_worker_records_run_failed_event_and_failure_type(session_factory, monkeypatch):
    monkeypatch.setattr(runner, "SessionLocal", session_factory)
    task_spec = {
        "input": {"url": "https://example.com"},
        "agent": {"max_steps": 0, "timeout_seconds": 10},
        "tools": ["browser"],
        "evaluation": [{"type": "json_schema"}],
    }
    with session_factory() as db:
        task = Task(task_key="failing_demo", name="Failing Demo", spec=task_spec)
        db.add(task)
        db.flush()
        run = Run(task_id=task.id, status="queued", model="mock", input=task_spec["input"])
        db.add(run)
        db.commit()
        run_id = run.id

    asyncio.run(runner._execute_run(run_id))

    with session_factory() as db:
        run = db.get(Run, run_id)
        steps = db.scalars(select(Step).where(Step.run_id == run_id).order_by(Step.step_index)).all()
        events = db.scalars(select(RunEvent).where(RunEvent.run_id == run_id).order_by(RunEvent.id)).all()

    assert run.status == "failed"
    assert run.failure_type == "MAX_STEPS_EXCEEDED"
    assert run.total_steps == 1
    assert steps[0].error == "MAX_STEPS_EXCEEDED"
    assert "run_failed" in {event.event_type for event in events}
