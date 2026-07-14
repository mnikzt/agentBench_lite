import asyncio
import time
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.events import record_event
from app.models.run import Run
from app.models.step import Step
from app.runtime.llm_client import LLMClient
from app.tools.registry import ToolRegistry


class ReActRuntime:
    def __init__(self, db: Session, llm_client: LLMClient | None = None) -> None:
        self.db = db
        self.llm_client = llm_client
        self.tools: ToolRegistry | None = None

    async def run(self, run_id: str, task_spec: dict, run_input: dict | None) -> dict:
        timeout_seconds = task_spec.get("agent", {}).get("timeout_seconds")
        if timeout_seconds:
            async with asyncio.timeout(float(timeout_seconds)):
                return await self._run_loop(run_id, task_spec, run_input)
        return await self._run_loop(run_id, task_spec, run_input)

    async def _run_loop(self, run_id: str, task_spec: dict, run_input: dict | None) -> dict:
        run = self.db.get(Run, run_id)
        if not run:
            raise ValueError(f"Run not found: {run_id}")

        allowed_tools = task_spec.get("tools") or []
        self.tools = ToolRegistry(allowed_tools=allowed_tools)
        max_steps = int(task_spec.get("agent", {}).get("max_steps", 8))
        max_tool_errors = int(task_spec.get("agent", {}).get("max_tool_errors", 3))
        consecutive_tool_errors = 0
        observations: list[str] = []
        final_output: dict | None = None
        record_event(self.db, run_id, "run_started", {"run_id": run_id})
        self.db.commit()

        for step_index in range(max_steps):
            step_start = time.perf_counter()
            record_event(self.db, run_id, "step_started", {"step_index": step_index})
            self.db.commit()

            if not self.llm_client:
                raise RuntimeError("LLM client is not configured")
            action = await self.llm_client.next_action(task_spec, run_input, observations)
            usage = action.get("_usage", {})
            if action.get("action") == "final":
                final_output = action.get("final_output") or {}
                self._record_step(
                    run_id=run_id,
                    step_index=step_index,
                    phase="final",
                    thought=action.get("thought"),
                    action="final",
                    latency_ms=int((time.perf_counter() - step_start) * 1000),
                    observation="Final answer produced",
                    tokens=int(usage.get("tokens", 0)),
                    cost_usd=Decimal(str(usage.get("cost_usd", 0))),
                )
                break

            tool_name = action.get("tool_name")
            tool_input = action.get("tool_input") or {}
            record_event(
                self.db,
                run_id,
                "tool_called",
                {"step_index": step_index, "tool_name": tool_name, "tool_input": tool_input},
            )
            self.db.commit()

            result = await self.tools.run(tool_name, tool_input)
            if result.error:
                consecutive_tool_errors += 1
                observations.append(result.observation or f"TOOL_ERROR: {result.error}")
            else:
                consecutive_tool_errors = 0
                observations.append(result.observation)
            self._record_step(
                run_id=run_id,
                step_index=step_index,
                phase="tool",
                thought=action.get("thought"),
                action="tool",
                tool_name=tool_name,
                tool_input=tool_input,
                tool_output=result.output,
                observation=result.observation,
                error=result.error,
                failure_type="TOOL_ERROR" if result.error else None,
                latency_ms=result.latency_ms,
                tokens=int(usage.get("tokens", 0)),
                cost_usd=Decimal(str(usage.get("cost_usd", 0))),
            )
            record_event(
                self.db,
                run_id,
                "tool_result",
                {
                    "step_index": step_index,
                    "tool_name": tool_name,
                    "error": result.error,
                    "observation": result.observation[:1000],
                },
            )
            self.db.commit()
            if consecutive_tool_errors >= max_tool_errors:
                raise RuntimeError(f"TOOL_ERROR: {result.error}")
        else:
            raise RuntimeError("MAX_STEPS_EXCEEDED")

        if final_output is None:
            raise RuntimeError("No final output produced")

        run.final_output = final_output
        self._update_totals(run)
        record_event(self.db, run_id, "run_finished", {"run_id": run_id, "final_output": final_output})
        self.db.add(run)
        self.db.commit()
        return final_output

    def _record_step(
        self,
        *,
        run_id: str,
        step_index: int,
        phase: str,
        thought: str | None,
        action: str,
        latency_ms: int,
        tool_name: str | None = None,
        tool_input: dict | None = None,
        tool_output: dict | None = None,
        observation: str | None = None,
        error: str | None = None,
        failure_type: str | None = None,
        tokens: int = 0,
        cost_usd: Decimal = Decimal("0"),
    ) -> Step:
        step = Step(
            run_id=run_id,
            step_index=step_index,
            phase=phase,
            thought=thought,
            action=action,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
            observation=observation,
            error=error,
            failure_type=failure_type,
            latency_ms=latency_ms,
            tokens=tokens,
            cost_usd=cost_usd,
        )
        self.db.add(step)
        self.db.flush()
        return step

    def _update_totals(self, run: Run) -> None:
        steps = self.db.scalars(select(Step).where(Step.run_id == run.id)).all()
        run.total_steps = len(steps)
        run.total_latency_ms = sum(step.latency_ms or 0 for step in steps)
        run.total_tokens = sum(step.tokens for step in steps)
        run.total_cost_usd = sum((step.cost_usd for step in steps), Decimal("0"))
