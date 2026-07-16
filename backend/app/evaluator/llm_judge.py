import json
import logging
from typing import Any

from app.core.config import get_settings
from app.evaluator.result import EvaluationResult
from app.models.run import Run
from app.models.step import Step
from app.runtime.llm_client import build_openai_sdk_client, has_openai_compatible_config

logger = logging.getLogger(__name__)


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
        if not has_openai_compatible_config():
            logger.warning("No LLM provider configured; llm_judge is using mock scores.")
            return await MockLlmJudgeEvaluator().evaluate(run, steps, spec)

        client = build_openai_sdk_client()
        request: dict[str, Any] = {
            "model": settings.judge_model,
            "temperature": 0,
            "messages": [
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
        }
        if settings.openai_use_json_response_format:
            request["response_format"] = {"type": "json_object"}
        response = await client.chat.completions.create(**request)
        if not response.choices:
            raise RuntimeError("LLM judge returned no choices.")
        raw = response.choices[0].message.content or "{}"
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"LLM judge returned non-JSON response: {raw[:200]}") from exc
        raw_score = parsed.get("score", 0)
        try:
            score = max(0.0, min(1.0, float(raw_score)))
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f"LLM judge returned non-numeric score: {raw_score!r}") from exc
        return EvaluationResult(
            self.evaluator_type,
            score,
            bool(parsed.get("passed", False)),
            {"rubric": rubric, "judge_model": settings.judge_model, "raw_output": parsed},
        )
