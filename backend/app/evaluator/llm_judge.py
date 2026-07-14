import json

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.evaluator.result import EvaluationResult
from app.models.run import Run
from app.models.step import Step


class MockLlmJudgeEvaluator:
    evaluator_type = "llm_judge"

    async def evaluate(self, run: Run, steps: list[Step], spec: dict) -> EvaluationResult:
        config = next(
            (item for item in spec.get("evaluation", []) if item.get("type") == "llm_judge"),
            {},
        )
        rubric = config.get("rubric", "Judge whether the final output satisfies the task.")
        passed = bool(run.final_output)
        return EvaluationResult(
            self.evaluator_type,
            0.7 if passed else 0.0,
            passed,
            {
                "rubric": rubric,
                "reason": "Mock judge passed when final_output is present.",
                "judge_model": "mock",
            },
        )


class LlmJudgeEvaluator:
    evaluator_type = "llm_judge"

    async def evaluate(self, run: Run, steps: list[Step], spec: dict) -> EvaluationResult:
        config = next(
            (item for item in spec.get("evaluation", []) if item.get("type") == "llm_judge"),
            {},
        )
        rubric = config.get("rubric", "Judge whether the final output satisfies the task.")
        settings = get_settings()
        if not settings.openai_api_key:
            return await MockLlmJudgeEvaluator().evaluate(run, steps, spec)

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model=settings.judge_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "Return JSON with score between 0 and 1, passed boolean, and reason.",
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "rubric": rubric,
                            "task": spec,
                            "final_output": run.final_output,
                            "steps": [
                                {
                                    "thought": step.thought,
                                    "tool_name": step.tool_name,
                                    "observation": step.observation,
                                }
                                for step in steps
                            ],
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        )
        raw = response.choices[0].message.content or "{}"
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"LLM judge returned non-JSON response: {raw[:200]}") from exc
        score = max(0.0, min(1.0, float(parsed.get("score", 0))))
        return EvaluationResult(
            self.evaluator_type,
            score,
            bool(parsed.get("passed", False)),
            {"rubric": rubric, "judge_model": settings.judge_model, "raw_output": parsed},
        )
