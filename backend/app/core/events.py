import asyncio
import json
import time
from collections.abc import AsyncIterator, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.states import TERMINAL_RUN_STATUSES
from app.models.run import Run
from app.models.run import RunEvent


def record_event(db: Session, run_id: str, event_type: str, payload: dict) -> RunEvent:
    event = RunEvent(run_id=run_id, event_type=event_type, payload=payload)
    db.add(event)
    db.flush()
    return event


def format_sse(event: RunEvent) -> str:
    data = {
        "id": event.id,
        "type": event.event_type,
        "payload": event.payload,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }
    return f"id: {event.id}\nevent: {event.event_type}\ndata: {json.dumps(data)}\n\n"


async def stream_run_events(
    db_factory: Callable[[], Session],
    run_id: str,
    *,
    after_id: int = 0,
    poll_interval: float = 0.5,
    keepalive_interval: float = 15,
) -> AsyncIterator[str]:
    last_id = after_id
    last_keepalive = time.monotonic()
    while True:
        with db_factory() as db:
            events = db.scalars(
                select(RunEvent)
                .where(RunEvent.run_id == run_id, RunEvent.id > last_id)
                .order_by(RunEvent.id.asc())
            ).all()
            for event in events:
                last_id = event.id
                yield format_sse(event)

            run = db.get(Run, run_id)
            if not run or run.status in TERMINAL_RUN_STATUSES:
                return

        if time.monotonic() - last_keepalive >= keepalive_interval:
            last_keepalive = time.monotonic()
            yield ": keepalive\n\n"
        await asyncio.sleep(poll_interval)
