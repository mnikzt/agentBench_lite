from dataclasses import dataclass


@dataclass
class EvaluationResult:
    evaluator_type: str
    score: float
    passed: bool
    details: dict
    error: str | None = None
