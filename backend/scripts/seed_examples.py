from pathlib import Path

import yaml
from sqlalchemy import select

from app.core.database import Base, SessionLocal, engine
from app.models import *  # noqa: F403
from app.models.task import Task
from app.models.task_set import TaskSet, TaskSetItem


ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples"


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        for path in sorted((EXAMPLES / "tasks").glob("*.yaml")):
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            task = db.scalar(select(Task).where(Task.task_key == data["id"]))
            spec = {
                "input": data.get("input"),
                "agent": data.get("agent", {}),
                "tools": data.get("tools", []),
                "expected_output": data.get("expected_output", {}),
                "evaluation": data.get("evaluation", []),
            }
            if task:
                task.name = data["name"]
                task.description = data.get("description")
                task.spec = spec
            else:
                db.add(
                    Task(
                        task_key=data["id"],
                        name=data["name"],
                        description=data.get("description"),
                        spec=spec,
                    )
                )
        db.commit()

        for path in sorted((EXAMPLES / "task_sets").glob("*.yaml")):
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            task_set = db.scalar(select(TaskSet).where(TaskSet.task_set_key == data["id"]))
            if not task_set:
                task_set = TaskSet(
                    task_set_key=data["id"],
                    name=data["name"],
                    description=data.get("description"),
                )
                db.add(task_set)
                db.flush()
            else:
                task_set.name = data["name"]
                task_set.description = data.get("description")

            for index, task_key in enumerate(data.get("tasks", [])):
                task = db.scalar(select(Task).where(Task.task_key == task_key))
                if not task:
                    continue
                existing = db.scalar(
                    select(TaskSetItem).where(
                        TaskSetItem.task_set_id == task_set.id,
                        TaskSetItem.task_id == task.id,
                    )
                )
                if not existing:
                    db.add(TaskSetItem(task_set_id=task_set.id, task_id=task.id, sort_order=index))
        db.commit()

    print("Seeded AgentBench Lite example tasks and task sets.")


if __name__ == "__main__":
    main()
