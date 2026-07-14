"""Initial AgentBench Lite schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-14
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("task_key", sa.String(length=128), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("spec", sa.JSON(), nullable=False),
        sa.Column("tags", sa.JSON()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tasks_task_key", "tasks", ["task_key"])

    op.create_table(
        "task_sets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("task_set_key", sa.String(length=128), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("tags", sa.JSON()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_task_sets_task_set_key", "task_sets", ["task_set_key"])

    op.create_table(
        "task_set_items",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("task_set_id", sa.String(length=36), sa.ForeignKey("task_sets.id"), nullable=False),
        sa.Column("task_id", sa.String(length=36), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("sort_order", sa.Integer(), default=0),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("task_set_id", "task_id", name="uq_task_set_item"),
    )

    op.create_table(
        "benchmark_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("task_set_id", sa.String(length=36), sa.ForeignKey("task_sets.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("summary", sa.JSON()),
        sa.Column("planned_runs", sa.Integer(), default=0),
        sa.Column("completed_runs", sa.Integer(), default=0),
        sa.Column("failed_runs", sa.Integer(), default=0),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("finished_at", sa.DateTime()),
    )
    op.create_index("ix_benchmark_runs_status", "benchmark_runs", ["status"])

    op.create_table(
        "runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("task_id", sa.String(length=36), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("benchmark_run_id", sa.String(length=36), sa.ForeignKey("benchmark_runs.id")),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("agent_mode", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("prompt_key", sa.String(length=128)),
        sa.Column("runtime_key", sa.String(length=64)),
        sa.Column("input", sa.JSON()),
        sa.Column("final_output", sa.JSON()),
        sa.Column("error", sa.Text()),
        sa.Column("failure_type", sa.String(length=64)),
        sa.Column("score", sa.Numeric(6, 4)),
        sa.Column("passed", sa.Boolean()),
        sa.Column("total_steps", sa.Integer(), default=0),
        sa.Column("total_latency_ms", sa.Integer(), default=0),
        sa.Column("total_tokens", sa.Integer(), default=0),
        sa.Column("total_cost_usd", sa.Numeric(12, 6), default=0),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("finished_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_runs_status", "runs", ["status"])

    op.create_table(
        "steps",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("run_id", sa.String(length=36), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("step_index", sa.Integer(), nullable=False),
        sa.Column("phase", sa.String(length=64)),
        sa.Column("thought", sa.Text()),
        sa.Column("action", sa.String(length=128)),
        sa.Column("tool_name", sa.String(length=128)),
        sa.Column("tool_input", sa.JSON()),
        sa.Column("tool_output", sa.JSON()),
        sa.Column("observation", sa.Text()),
        sa.Column("error", sa.Text()),
        sa.Column("failure_type", sa.String(length=64)),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("tokens", sa.Integer(), default=0),
        sa.Column("cost_usd", sa.Numeric(12, 6), default=0),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("run_id", "step_index", name="uq_step_run_index"),
    )
    op.create_index("ix_steps_run_id", "steps", ["run_id"])

    op.create_table(
        "evaluations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("run_id", sa.String(length=36), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("evaluator_type", sa.String(length=64), nullable=False),
        sa.Column("score", sa.Numeric(6, 4)),
        sa.Column("passed", sa.Boolean()),
        sa.Column("details", sa.JSON()),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_evaluations_run_id", "evaluations", ["run_id"])

    op.create_table(
        "run_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(length=36), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_run_events_run_id", "run_events", ["run_id"])

    op.create_table(
        "benchmark_run_items",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("benchmark_run_id", sa.String(length=36), sa.ForeignKey("benchmark_runs.id"), nullable=False),
        sa.Column("run_id", sa.String(length=36), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("task_id", sa.String(length=36), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("prompt_key", sa.String(length=128), nullable=False),
        sa.Column("runtime_key", sa.String(length=64), nullable=False),
        sa.Column("repeat_index", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "benchmark_run_id",
            "task_id",
            "model",
            "prompt_key",
            "runtime_key",
            "repeat_index",
            name="uq_benchmark_matrix_cell",
        ),
    )


def downgrade() -> None:
    op.drop_table("benchmark_run_items")
    op.drop_table("run_events")
    op.drop_table("evaluations")
    op.drop_table("steps")
    op.drop_table("runs")
    op.drop_table("benchmark_runs")
    op.drop_table("task_set_items")
    op.drop_table("task_sets")
    op.drop_table("tasks")
