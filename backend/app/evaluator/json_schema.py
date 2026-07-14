from jsonschema import ValidationError, validate

from app.evaluator.result import EvaluationResult
from app.models.run import Run
from app.models.step import Step


class JsonSchemaEvaluator:
    evaluator_type = "json_schema"

    async def evaluate(self, run: Run, steps: list[Step], spec: dict) -> EvaluationResult:
        schema = spec.get("expected_output", {}).get("schema")
        if not schema:
            return EvaluationResult(self.evaluator_type, 1.0, True, {"reason": "No schema configured"})
        try:
            validate(instance=run.final_output or {}, schema=schema)
            return EvaluationResult(self.evaluator_type, 1.0, True, {"reason": "Output matches schema"})
        except ValidationError as exc:
            return EvaluationResult(
                self.evaluator_type,
                0.0,
                False,
                {"reason": exc.message, "path": list(exc.path)},
                error=exc.message,
            )
