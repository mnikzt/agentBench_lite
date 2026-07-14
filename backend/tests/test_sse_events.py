import asyncio
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.core.events import record_event, stream_run_events
from app.models.run import Run
from app.models.task import Task


@pytest.fixture
def session_factory(tmp_path) -> Generator[sessionmaker[Session], None, None]:
    engine = create_engine(f"sqlite:///{tmp_path / 'sse.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    try:
        yield factory
    finally:
        Base.metadata.drop_all(bind=engine)


def test_stream_run_events_yields_named_sse_events(session_factory):
    with session_factory() as db:
        task = Task(task_key="sse_demo", name="SSE Demo", spec={})
        db.add(task)
        db.flush()
        run = Run(task_id=task.id, status="success", model="mock")
        db.add(run)
        db.flush()
        record_event(db, run.id, "run_finished", {"run_id": run.id})
        db.commit()
        run_id = run.id

    async def collect_one() -> str:
        stream = stream_run_events(session_factory, run_id)
        return await anext(stream)

    payload = asyncio.run(collect_one())

    assert "event: run_finished" in payload
    assert "\"type\": \"run_finished\"" in payload
