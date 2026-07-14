from app.evaluator.result import EvaluationResult
from app.models.run import Run
from app.models.step import Step


class ExactMatchEvaluator:
    evaluator_type = "exact_match"

    async def evaluate(self, run: Run, steps: list[Step], spec: dict) -> EvaluationResult:
        expected = spec.get("expected_output", {}).get("value")
        actual = run.final_output
        passed = actual == expected
        return EvaluationResult(
            self.evaluator_type,
            1.0 if passed else 0.0,
            passed,
            {"expected": expected, "actual": actual},
        )
