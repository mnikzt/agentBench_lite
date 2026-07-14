from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models.task import Task
from app.models.task_set import TaskSet, TaskSetItem
from app.schemas.tasks import TaskSetCreate, TaskSetItemCreate, TaskSetRead

router = APIRouter(prefix="/api/task-sets", tags=["task-sets"])


def serialize_task_set(task_set: TaskSet) -> dict:
    return {
        "id": task_set.id,
        "task_set_key": task_set.task_set_key,
        "name": task_set.name,
        "description": task_set.description,
        "tags": task_set.tags,
        "created_at": task_set.created_at,
        "updated_at": task_set.updated_at,
        "tasks": [item.task for item in sorted(task_set.items, key=lambda item: item.sort_order)],
    }


@router.post("", response_model=TaskSetRead, status_code=status.HTTP_201_CREATED)
def create_task_set(payload: TaskSetCreate, db: Session = Depends(get_db)) -> dict:
    existing = db.scalar(select(TaskSet).where(TaskSet.task_set_key == payload.task_set_key))
    if existing:
        raise HTTPException(status_code=409, detail="Task set key already exists")

    task_set = TaskSet(**payload.model_dump())
    db.add(task_set)
    db.commit()
    db.refresh(task_set)
    return serialize_task_set(task_set)


@router.get("", response_model=list[TaskSetRead])
def list_task_sets(db: Session = Depends(get_db)) -> list[dict]:
    task_sets = db.scalars(
        select(TaskSet).options(selectinload(TaskSet.items).selectinload(TaskSetItem.task))
    ).all()
    return [serialize_task_set(task_set) for task_set in task_sets]


@router.get("/{task_set_key}", response_model=TaskSetRead)
def get_task_set(task_set_key: str, db: Session = Depends(get_db)) -> dict:
    task_set = db.scalar(
        select(TaskSet)
        .where(TaskSet.task_set_key == task_set_key)
        .options(selectinload(TaskSet.items).selectinload(TaskSetItem.task))
    )
    if not task_set:
        raise HTTPException(status_code=404, detail="Task set not found")
    return serialize_task_set(task_set)


@router.post("/{task_set_key}/items", response_model=TaskSetRead)
def add_task_set_item(
    task_set_key: str,
    payload: TaskSetItemCreate,
    db: Session = Depends(get_db),
) -> dict:
    task_set = db.scalar(select(TaskSet).where(TaskSet.task_set_key == task_set_key))
    task = db.scalar(select(Task).where(Task.task_key == payload.task_key))
    if not task_set or not task:
        raise HTTPException(status_code=404, detail="Task set or task not found")

    existing = db.scalar(
        select(TaskSetItem).where(
            TaskSetItem.task_set_id == task_set.id,
            TaskSetItem.task_id == task.id,
        )
    )
    if not existing:
        db.add(TaskSetItem(task_set_id=task_set.id, task_id=task.id, sort_order=payload.sort_order))
        db.commit()

    task_set = db.scalar(
        select(TaskSet)
        .where(TaskSet.id == task_set.id)
        .options(selectinload(TaskSet.items).selectinload(TaskSetItem.task))
    )
    return serialize_task_set(task_set)


@router.delete("/{task_set_key}/items/{task_key}", status_code=status.HTTP_204_NO_CONTENT)
def remove_task_set_item(task_set_key: str, task_key: str, db: Session = Depends(get_db)) -> None:
    task_set = db.scalar(select(TaskSet).where(TaskSet.task_set_key == task_set_key))
    task = db.scalar(select(Task).where(Task.task_key == task_key))
    if not task_set or not task:
        raise HTTPException(status_code=404, detail="Task set or task not found")

    item = db.scalar(
        select(TaskSetItem).where(
            TaskSetItem.task_set_id == task_set.id,
            TaskSetItem.task_id == task.id,
        )
    )
    if item:
        db.delete(item)
        db.commit()
