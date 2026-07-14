import asyncio
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.models.run import Run
from app.models.step import Step
from app.models.task import Task
from app.runtime.llm_client import MockLLMClient
from app.runtime.react import ReActRuntime
from app.tools.registry import ToolRegistry


@pytest.fixture
def db(tmp_path) -> Generator[Session, None, None]:
    engine = create_engine(f"sqlite:///{tmp_path / 'runtime.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_react_runtime_records_steps_and_final_output(db: Session):
    task_spec = {
        "input": {
            "url": "https://example.com",
            "mock_page_text": "Example product page with a demo price.",
        },
        "agent": {"max_steps": 3, "timeout_seconds": 5},
        "tools": ["browser"],
        "expected_output": {
            "schema": {
                "type": "object",
                "properties": {"summary": {"type": "string"}},
            }
        },
    }
    task = Task(task_key="runtime_demo", name="Runtime Demo", spec=task_spec)
    db.add(task)
    db.flush()
    run = Run(task_id=task.id, status="running", model="mock", input=task_spec["input"])
    db.add(run)
    db.commit()

    final_output = asyncio.run(ReActRuntime(db, MockLLMClient()).run(run.id, task_spec, run.input))
    steps = db.scalars(select(Step).where(Step.run_id == run.id).order_by(Step.step_index)).all()

    assert final_output["summary"].startswith("Mock browser loaded")
    assert len(steps) == 2
    assert steps[0].tool_name == "browser"
    assert steps[0].tool_input["url"] == "https://example.com"
    assert steps[0].tool_output["text"] == "Example product page with a demo price."
    assert steps[1].action == "final"


def test_tool_registry_rejects_tools_not_in_allowlist():
    result = asyncio.run(ToolRegistry(allowed_tools=["file"]).run("http", {"url": "https://example.com"}))

    assert result.error == "TOOL_NOT_ALLOWED"


def test_tool_registry_empty_allowlist_rejects_all_tools():
    result = asyncio.run(ToolRegistry(allowed_tools=[]).run("http", {"url": "https://example.com"}))

    assert result.error == "TOOL_NOT_ALLOWED"
