import time

from app.tools.base import ToolResult


class BrowserTool:
    name = "browser"

    async def run(self, tool_input: dict) -> ToolResult:
        start = time.perf_counter()
        url = tool_input.get("url")
        if not url:
            return ToolResult({}, "Missing url", 0, error="Missing url")

        text = str(tool_input.get("text") or f"Mock page text for {url}")
        title = str(tool_input.get("title") or "Mock Browser Page")
        latency_ms = int((time.perf_counter() - start) * 1000)
        return ToolResult(
            output={"url": url, "title": title, "text": text},
            observation=f"Mock browser loaded {url} with title '{title}'. Text: {text[:500]}",
            latency_ms=latency_ms,
        )
