from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.events import record_event
from app.evaluator.base import Evaluator
from app.evaluator.exact_match import ExactMatchEvaluator
from app.evaluator.json_schema import JsonSchemaEvaluator
from app.evaluator.llm_judge import LlmJudgeEvaluator
from app.evaluator.result import EvaluationResult
from app.models.evaluation import Evaluation
from app.models.run import Run
from app.models.step import Step


class EvaluatorPipeline:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._evaluators: dict[str, Evaluator] = {
            "json_schema": JsonSchemaEvaluator(),
            "exact_match": ExactMatchEvaluator(),
            "llm_judge": LlmJudgeEvaluator(),
        }

    async def evaluate(self, run: Run, spec: dict) -> list[EvaluationResult]:
        steps = list(self.db.scalars(select(Step).where(Step.run_id == run.id).order_by(Step.step_index)).all())
        configs = spec.get("evaluation") or [{"type": "json_schema"}]
        results: list[EvaluationResult] = []
        for config in configs:
            evaluator_type = config.get("type")
            evaluator = self._evaluators.get(evaluator_type)
            if not evaluator:
                continue
            result = await evaluator.evaluate(run, steps, spec)
            results.append(result)
            self.db.add(
                Evaluation(
                    run_id=run.id,
                    evaluator_type=result.evaluator_type,
                    score=Decimal(str(result.score)),
                    passed=result.passed,
                    details=result.details,
                    error=result.error,
                )
            )

        if results:
            run.score = Decimal(str(sum(result.score for result in results) / len(results)))
            run.passed = all(result.passed for result in results)
        else:
            run.score = Decimal("0")
            run.passed = False

        record_event(
            self.db,
            run.id,
            "evaluation_finished",
            {
                "score": float(run.score),
                "passed": run.passed,
                "results": [
                    {
                        "type": result.evaluator_type,
                        "score": result.score,
                        "passed": result.passed,
                        "error": result.error,
                    }
                    for result in results
                ],
            },
        )
        self.db.add(run)
        return results
