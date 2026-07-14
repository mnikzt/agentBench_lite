from app.benchmark.matrix import expand_matrix
from app.models.task import Task


def test_expand_matrix_creates_cartesian_product():
    tasks = [
        Task(id="t1", task_key="task_1", name="Task 1", spec={}),
        Task(id="t2", task_key="task_2", name="Task 2", spec={}),
    ]

    cells = expand_matrix(
        tasks,
        models=["gpt-a", "gpt-b"],
        prompts=["baseline"],
        runtimes=["react"],
        repeat=3,
    )

    assert len(cells) == 12
    assert {cell.repeat_index for cell in cells} == {0, 1, 2}
    assert {cell.model for cell in cells} == {"gpt-a", "gpt-b"}
