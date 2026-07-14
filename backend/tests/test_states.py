import pytest

from app.core.states import InvalidStateTransition, transition_run
from app.models.run import Run


class DummyDb:
    def add(self, value):
        self.value = value


def test_transition_run_rejects_terminal_transition():
    run = Run(task_id="task", status="success", model="model")

    with pytest.raises(InvalidStateTransition):
        transition_run(DummyDb(), run, "running")


def test_transition_run_sets_started_and_finished_times():
    db = DummyDb()
    run = Run(task_id="task", status="queued", model="model")

    transition_run(db, run, "running")
    assert run.started_at is not None

    transition_run(db, run, "failed", error="boom", failure_type="UNKNOWN")
    assert run.finished_at is not None
    assert run.error == "boom"
    assert run.failure_type == "UNKNOWN"
