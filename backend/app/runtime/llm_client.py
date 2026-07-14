import json
from typing import Any, Protocol

from openai import AsyncOpenAI

from app.core.config import get_settings


class LLMClient(Protocol):
    async def next_action(self, task_spec: dict, run_input: dict | None, observations: list[str]) -> dict:
        ...


class MockLLMClient:
    """Deterministic local client for running the MVP without a real LLM."""

    async def next_action(self, task_spec: dict, run_input: dict | None, observations: list[str]) -> dict:
        data = run_input or task_spec.get("input") or {}
        tools = task_spec.get("tools") or []
        url = data.get("url")
        file_path = data.get("file_path") or data.get("path")
        if not observations and file_path and "file" in tools:
            return {
                "thought": "Read the demo file before answering.",
                "action": "tool",
                "tool_name": "file",
                "tool_input": {"path": file_path},
            }
        if not observations and url and "browser" in tools:
            return {
                "thought": "Use the mock browser to inspect the page text.",
                "action": "tool",
                "tool_name": "browser",
                "tool_input": {"url": url, "text": data.get("mock_page_text")},
            }
        if not observations and url and "http" in tools:
            return {
                "thought": "Fetch the URL with the HTTP tool.",
                "action": "tool",
                "tool_name": "http",
                "tool_input": {"url": url},
            }
        return {
            "thought": "Produce a structured final answer from the available observations.",
            "action": "final",
            "final_output": _fallback_output(task_spec, data, observations),
            "_usage": {"tokens": 0, "cost_usd": 0},
        }


class OpenAICompatibleLLMClient:
    def __init__(self, model: str | None = None) -> None:
        settings = get_settings()
        self.model = model or settings.default_llm_model
        self.api_key = settings.openai_api_key
        self.cost_per_1k_tokens = settings.model_cost_per_1k_tokens_usd
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None

    async def next_action(self, task_spec: dict, run_input: dict | None, observations: list[str]) -> dict:
        if not self.client:
            return await self._fallback_action(task_spec, run_input, observations)

        prompt = self._build_prompt(task_spec, run_input, observations)
        response = await self.client.chat.completions.create(
            model=self.model,
            temperature=task_spec.get("agent", {}).get("temperature", 0),
            messages=[
                {
                    "role": "system",
                    "content": "Return only JSON with thought, action, tool_name, tool_input, final_output.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        try:
            action = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"LLM returned non-JSON response: {content[:200]}") from exc
        total_tokens = response.usage.total_tokens if response.usage else 0
        action["_usage"] = {
            "tokens": total_tokens,
            "cost_usd": (total_tokens / 1000) * self.cost_per_1k_tokens.get(self.model, 0),
        }
        return action

    def _build_prompt(self, task_spec: dict, run_input: dict | None, observations: list[str]) -> str:
        return json.dumps(
            {
                "task": task_spec,
                "input": run_input,
                "observations": observations,
                "instruction": "Choose one tool call or produce final_output. action must be tool or final.",
            },
            ensure_ascii=False,
        )

    async def _fallback_action(self, task_spec: dict, run_input: dict | None, observations: list[str]) -> dict[str, Any]:
        return await MockLLMClient().next_action(task_spec, run_input, observations)


def build_llm_client(model: str | None = None) -> LLMClient:
    if get_settings().openai_api_key:
        return OpenAICompatibleLLMClient(model)
    return MockLLMClient()


def _fallback_output(task_spec: dict, run_input: dict, observations: list[str]) -> dict:
    schema = task_spec.get("expected_output", {}).get("schema", {})
    properties = schema.get("properties", {})
    output: dict[str, Any] = {}
    for key, spec in properties.items():
        if key in run_input:
            output[key] = run_input[key]
        elif spec.get("type") == "number":
            output[key] = 0
        elif spec.get("type") == "boolean":
            output[key] = False
        elif spec.get("type") == "array":
            output[key] = []
        else:
            output[key] = observations[-1][:500] if observations else ""
    if not output:
        output = {"answer": observations[-1] if observations else run_input}
    return output
