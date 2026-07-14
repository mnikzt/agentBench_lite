from typing import Protocol

from app.evaluator.result import EvaluationResult
from app.models.run import Run
from app.models.step import Step


class Evaluator(Protocol):
    evaluator_type: str

    async def evaluate(self, run: Run, steps: list[Step], spec: dict) -> EvaluationResult:
        ...
