import asyncio

import pytest

from app.core.config import get_settings
from app.evaluator.llm_judge import LlmJudgeEvaluator
from app.models.run import Run
from app.runtime.llm_client import MockLLMClient, OpenAICompatibleLLMClient, build_llm_client


class _FakeCompletions:
    def __init__(self) -> None:
        self.request = None

    async def create(self, **kwargs):
        self.request = kwargs
        return _FakeResponse()


class _FakeChat:
    def __init__(self, completions: _FakeCompletions) -> None:
        self.completions = completions


class _FakeClient:
    def __init__(self, completions: _FakeCompletions) -> None:
        self.chat = _FakeChat(completions)


class _FakeUsage:
    total_tokens = 12


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str = '{"thought":"done","action":"final","final_output":{"answer":"ok"}}') -> None:
        self.choices = [_FakeChoice(content)]
        self.usage = _FakeUsage()


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_build_llm_client_uses_mock_without_provider_config(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    get_settings.cache_clear()

    client = build_llm_client()

    assert isinstance(client, MockLLMClient)


def test_build_llm_client_uses_openai_compatible_for_base_url(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
    get_settings.cache_clear()

    client = build_llm_client("qwen2.5:7b")

    assert isinstance(client, OpenAICompatibleLLMClient)
    assert client.model == "qwen2.5:7b"
    assert client.base_url == "http://localhost:11434/v1"


def test_openai_compatible_client_can_disable_json_response_format(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("OPENAI_USE_JSON_RESPONSE_FORMAT", "false")
    get_settings.cache_clear()
    completions = _FakeCompletions()
    client = OpenAICompatibleLLMClient("qwen2.5:7b")
    client.client = _FakeClient(completions)

    action = asyncio.run(client.next_action({"agent": {}}, {}, []))

    assert action["final_output"] == {"answer": "ok"}
    assert completions.request["model"] == "qwen2.5:7b"
    assert "response_format" not in completions.request


def test_llm_judge_can_disable_json_response_format(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("OPENAI_USE_JSON_RESPONSE_FORMAT", "false")
    get_settings.cache_clear()
    completions = _FakeCompletions()
    monkeypatch.setattr("app.evaluator.llm_judge.build_openai_sdk_client", lambda: _FakeClient(completions))
    run = Run(final_output={"answer": "ok"})

    result = asyncio.run(LlmJudgeEvaluator().evaluate(run, [], {"evaluation": [{"type": "llm_judge"}]}))

    assert result.score == 0
    assert completions.request["model"] == "gpt-4o-mini"
    assert "response_format" not in completions.request


def test_llm_judge_rejects_non_numeric_score(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
    get_settings.cache_clear()
    completions = _FakeCompletions()

    async def create_non_numeric_score(**kwargs):
        completions.request = kwargs
        return _FakeResponse('{"score":"high","passed":true,"reason":"ok"}')

    completions.create = create_non_numeric_score
    monkeypatch.setattr("app.evaluator.llm_judge.build_openai_sdk_client", lambda: _FakeClient(completions))
    run = Run(final_output={"answer": "ok"})

    with pytest.raises(RuntimeError, match="non-numeric score"):
        asyncio.run(LlmJudgeEvaluator().evaluate(run, [], {"evaluation": [{"type": "llm_judge"}]}))
