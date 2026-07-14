from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.task import new_uuid


class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    task_set_id: Mapped[str] = mapped_column(ForeignKey("task_sets.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    summary: Mapped[dict | None] = mapped_column(JSON)
    planned_runs: Mapped[int] = mapped_column(default=0)
    completed_runs: Mapped[int] = mapped_column(default=0)
    failed_runs: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)

    task_set = relationship("TaskSet", back_populates="benchmark_runs")
    items = relationship("BenchmarkRunItem", back_populates="benchmark_run", cascade="all, delete-orphan")
    runs = relationship("Run", back_populates="benchmark_run")


class BenchmarkRunItem(Base):
    __tablename__ = "benchmark_run_items"
    __table_args__ = (
        UniqueConstraint(
            "benchmark_run_id",
            "task_id",
            "model",
            "prompt_key",
            "runtime_key",
            "repeat_index",
            name="uq_benchmark_matrix_cell",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    benchmark_run_id: Mapped[str] = mapped_column(ForeignKey("benchmark_runs.id"), nullable=False)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), nullable=False)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_key: Mapped[str] = mapped_column(String(128), nullable=False)
    runtime_key: Mapped[str] = mapped_column(String(64), nullable=False)
    repeat_index: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    benchmark_run = relationship("BenchmarkRun", back_populates="items")
    run = relationship("Run")
    task = relationship("Task")
