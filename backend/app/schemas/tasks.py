from datetime import datetime

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    task_key: str = Field(min_length=1, max_length=128)
    name: str
    description: str | None = None
    spec: dict
    tags: list[str] | None = None


class TaskRead(TaskCreate):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskSetCreate(BaseModel):
    task_set_key: str = Field(min_length=1, max_length=128)
    name: str
    description: str | None = None
    tags: list[str] | None = None


class TaskSetItemCreate(BaseModel):
    task_key: str
    sort_order: int = 0


class TaskSetRead(TaskSetCreate):
    id: str
    created_at: datetime
    updated_at: datetime
    tasks: list[TaskRead] = []

    model_config = {"from_attributes": True}
