from dataclasses import dataclass
from typing import Protocol


@dataclass
class ToolResult:
    output: dict
    observation: str
    latency_ms: int
    error: str | None = None


class Tool(Protocol):
    name: str

    async def run(self, tool_input: dict) -> ToolResult:
        ...
