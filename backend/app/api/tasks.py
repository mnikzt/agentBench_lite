from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.task import Task
from app.schemas.tasks import TaskCreate, TaskRead

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)) -> Task:
    existing = db.scalar(select(Task).where(Task.task_key == payload.task_key))
    if existing:
        raise HTTPException(status_code=409, detail="Task key already exists")

    task = Task(**payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("", response_model=list[TaskRead])
def list_tasks(db: Session = Depends(get_db)) -> list[Task]:
    return list(db.scalars(select(Task).order_by(Task.created_at.desc())).all())


@router.get("/{task_key}", response_model=TaskRead)
def get_task(task_key: str, db: Session = Depends(get_db)) -> Task:
    task = db.scalar(select(Task).where(Task.task_key == task_key))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_key}", response_model=TaskRead)
def update_task(task_key: str, payload: TaskCreate, db: Session = Depends(get_db)) -> Task:
    task = db.scalar(select(Task).where(Task.task_key == task_key))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    for key, value in payload.model_dump().items():
        setattr(task, key, value)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task
