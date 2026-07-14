from app.tools.base import Tool, ToolResult
from app.tools.browser_tool import BrowserTool
from app.tools.file_tool import FileTool
from app.tools.http_tool import HttpTool


class ToolRegistry:
    def __init__(self, tools: list[Tool] | None = None, allowed_tools: list[str] | None = None) -> None:
        tool_list = tools or [HttpTool(), FileTool(), BrowserTool()]
        self._tools = {tool.name: tool for tool in tool_list}
        self._allowed_tools = set(self._tools if allowed_tools is None else allowed_tools)

    async def run(self, tool_name: str, tool_input: dict) -> ToolResult:
        if tool_name not in self._allowed_tools:
            return ToolResult({}, f"Tool is not allowed for this task: {tool_name}", 0, error="TOOL_NOT_ALLOWED")
        tool = self._tools.get(tool_name)
        if not tool:
            return ToolResult({}, f"Unknown tool: {tool_name}", 0, error="Unknown tool")
        return await tool.run(tool_input)

    def names(self) -> list[str]:
        return sorted(self._tools)
