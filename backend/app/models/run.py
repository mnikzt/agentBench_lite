from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, JSON, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.task import new_uuid


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    benchmark_run_id: Mapped[str | None] = mapped_column(ForeignKey("benchmark_runs.id"))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    agent_mode: Mapped[str] = mapped_column(String(64), nullable=False, default="react")
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_key: Mapped[str | None] = mapped_column(String(128))
    runtime_key: Mapped[str] = mapped_column(String(64), default="react")
    input: Mapped[dict | None] = mapped_column(JSON)
    final_output: Mapped[dict | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    failure_type: Mapped[str | None] = mapped_column(String(64))
    score: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    passed: Mapped[bool | None] = mapped_column()
    total_steps: Mapped[int] = mapped_column(default=0)
    total_latency_ms: Mapped[int] = mapped_column(default=0)
    total_tokens: Mapped[int] = mapped_column(default=0)
    total_cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    task = relationship("Task", back_populates="runs")
    steps = relationship("Step", back_populates="run", cascade="all, delete-orphan")
    evaluations = relationship("Evaluation", back_populates="run", cascade="all, delete-orphan")
    events = relationship("RunEvent", back_populates="run", cascade="all, delete-orphan")
    benchmark_run = relationship("BenchmarkRun", back_populates="runs")


class RunEvent(Base):
    __tablename__ = "run_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    run = relationship("Run", back_populates="events")
