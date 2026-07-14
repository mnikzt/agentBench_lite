from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.run import Run


TERMINAL_RUN_STATUSES = {"success", "failed", "timeout", "cancelled"}

ALLOWED_RUN_TRANSITIONS = {
    "pending": {"queued", "cancelled"},
    "queued": {"running", "cancelled", "failed"},
    "running": {"evaluating", "failed", "timeout", "cancelled"},
    "evaluating": {"success", "failed"},
    "success": set(),
    "failed": set(),
    "timeout": set(),
    "cancelled": set(),
}


class InvalidStateTransition(ValueError):
    pass


def transition_run(
    db: Session,
    run: Run,
    status: str,
    *,
    error: str | None = None,
    failure_type: str | None = None,
) -> Run:
    allowed = ALLOWED_RUN_TRANSITIONS.get(run.status, set())
    if status not in allowed and status != run.status:
        raise InvalidStateTransition(f"Cannot transition run {run.id} from {run.status} to {status}")

    now = datetime.now(UTC)
    run.status = status
    run.error = error if error is not None else run.error
    run.failure_type = failure_type if failure_type is not None else run.failure_type
    if status == "running" and run.started_at is None:
        run.started_at = now
    if status in TERMINAL_RUN_STATUSES:
        run.finished_at = now
    db.add(run)
    return run
