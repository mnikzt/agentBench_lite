from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.task import new_uuid


class TaskSet(Base):
    __tablename__ = "task_sets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    task_set_key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    items = relationship("TaskSetItem", back_populates="task_set", cascade="all, delete-orphan")
    benchmark_runs = relationship("BenchmarkRun", back_populates="task_set")


class TaskSetItem(Base):
    __tablename__ = "task_set_items"
    __table_args__ = (UniqueConstraint("task_set_id", "task_id", name="uq_task_set_item"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    task_set_id: Mapped[str] = mapped_column(ForeignKey("task_sets.id"), nullable=False)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    task_set = relationship("TaskSet", back_populates="items")
    task = relationship("Task")
