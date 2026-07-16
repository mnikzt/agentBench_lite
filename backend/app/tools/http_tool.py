import time

import httpx

from app.tools.base import ToolResult
from app.tools.url_safety import validate_public_http_url, validate_public_response_peer


class HttpTool:
    name = "http"

    async def run(self, tool_input: dict) -> ToolResult:
        start = time.perf_counter()
        method = str(tool_input.get("method", "GET")).upper()
        if method != "GET":
            return ToolResult({}, "HTTP tool MVP only supports GET", 0, error="UNSUPPORTED_HTTP_METHOD")
        url = tool_input.get("url")
        if not url:
            return ToolResult({}, "Missing url", 0, error="Missing url")
        validation_error = await validate_public_http_url(str(url))
        if validation_error:
            return ToolResult({}, validation_error, 0, error=validation_error)

        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
                response = await client.get(url)
            peer_validation_error = validate_public_response_peer(response)
            if peer_validation_error:
                latency_ms = int((time.perf_counter() - start) * 1000)
                return ToolResult({}, peer_validation_error, latency_ms, error=peer_validation_error)
            text = response.text[:5000]
            latency_ms = int((time.perf_counter() - start) * 1000)
            return ToolResult(
                output={
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "text": text,
                },
                observation=f"HTTP {response.status_code} from {url}: {text[:500]}",
                latency_ms=latency_ms,
                error=None if response.is_success else f"HTTP {response.status_code}",
            )
        except httpx.HTTPError as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            return ToolResult({}, f"HTTP request failed: {exc}", latency_ms, error=str(exc))
