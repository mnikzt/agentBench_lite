import time
from pathlib import Path

from app.tools.base import ToolResult


class FileTool:
    name = "file"

    async def run(self, tool_input: dict) -> ToolResult:
        start = time.perf_counter()
        operation = tool_input.get("operation", "read")
        relative_path = tool_input.get("path")
        if not relative_path:
            return ToolResult({}, "Missing path", 0, error="Missing path")
        if operation != "read":
            return ToolResult({}, "File tool MVP only supports read", 0, error="UNSUPPORTED_FILE_OPERATION")

        try:
            path = self._safe_path(relative_path)
            text = path.read_text(encoding="utf-8")
            output = {"path": str(path), "text": text[:10000]}
            observation = f"Read {len(text)} characters from {relative_path}"
            return ToolResult(output, observation, int((time.perf_counter() - start) * 1000))
        except OSError as exc:
            return ToolResult({}, f"File operation failed: {exc}", int((time.perf_counter() - start) * 1000), str(exc))

    def _safe_path(self, relative_path: str) -> Path:
        root = (Path(__file__).resolve().parents[3] / "examples").resolve()
        path = (root / relative_path).resolve()
        if root not in path.parents and path != root:
            raise OSError("Path escapes workspace")
        return path
