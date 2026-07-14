from dataclasses import dataclass
from itertools import product

from app.models.task import Task


@dataclass(frozen=True)
class MatrixCell:
    task: Task
    model: str
    prompt_key: str
    runtime_key: str
    repeat_index: int


def expand_matrix(
    tasks: list[Task],
    models: list[str],
    prompts: list[str],
    runtimes: list[str],
    repeat: int,
) -> list[MatrixCell]:
    cells: list[MatrixCell] = []
    for task, model, prompt_key, runtime_key, repeat_index in product(
        tasks,
        models,
        prompts,
        runtimes,
        range(repeat),
    ):
        cells.append(
            MatrixCell(
                task=task,
                model=model,
                prompt_key=prompt_key,
                runtime_key=runtime_key,
                repeat_index=repeat_index,
            )
        )
    return cells
