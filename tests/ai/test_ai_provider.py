"""Tests for the generic AI chat provider."""

from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest

from eventweave.ai.ai_config import AIProviderConfig, AIProviderError
from eventweave.ai.ai_provider import AIChatProvider
from eventweave.ai.cache import SemanticCache
from eventweave.ai.provider import GenerationContext, ProviderConfig
from eventweave.ai.sidecar import SemanticSidecar
from eventweave.core.event import Event
from eventweave.core.scenario import Scenario
from eventweave.core.semantic import SemanticTask


class _FakeAIHandler(BaseHTTPRequestHandler):
    """Handler that captures the request and returns a fake completion."""

    requests: list[dict[str, Any]] = []
    auth_headers: list[str | None] = []
    status: int = 200
    failure_count: int = 0
    response_body: str | None = None

    def do_POST(self) -> None:  # noqa: N802
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length).decode("utf-8")
        _FakeAIHandler.requests.append(json.loads(body))
        _FakeAIHandler.auth_headers.append(self.headers.get("Authorization"))

        if _FakeAIHandler.failure_count > 0:
            _FakeAIHandler.failure_count -= 1
            self.send_response(503)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error":"service unavailable"}')
            return

        self.send_response(_FakeAIHandler.status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        response = _FakeAIHandler.response_body
        if response is None:
            response = json.dumps(
                {
                    "choices": [
                        {"message": {"content": "Generated refund reason from fake AI."}}
                    ]
                }
            )
        self.wfile.write(response.encode("utf-8"))

    def log_message(self, format: str, *args: Any) -> None:
        pass


@pytest.fixture
def fake_server() -> str:
    """Start a fake AI API server and return its base URL."""
    _FakeAIHandler.requests.clear()
    _FakeAIHandler.auth_headers.clear()
    _FakeAIHandler.status = 200
    _FakeAIHandler.failure_count = 0
    _FakeAIHandler.response_body = None

    server = HTTPServer(("127.0.0.1", 0), _FakeAIHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


@pytest.fixture
def task() -> SemanticTask:
    return SemanticTask(
        id="refund_reason",
        type="refund.reason",
        prompt="Write a refund reason.",
        valid_for=["refund.requested"],
    )


@pytest.fixture
def context() -> GenerationContext:
    scenario = Scenario(
        id="ecommerce_refund_flow",
        name="E-commerce refund flow",
        domain="ecommerce",
    )
    return GenerationContext(scenario=scenario, task=None, entities={})


def test_ai_provider_builds_chat_request(
    fake_server: str, task: SemanticTask, context: GenerationContext
) -> None:
    provider = AIChatProvider(
        ProviderConfig(
            "ai",
            base_url=fake_server,
            model="moonshot-v1-8k",
            api_key_env="EVENTWEAVE_AI_API_KEY",
        )
    )
    os.environ["EVENTWEAVE_AI_API_KEY"] = "test-key"

    asset = provider.generate(task, context)

    assert asset.text == "Generated refund reason from fake AI."
    assert asset.type == "refund.reason"
    assert len(_FakeAIHandler.requests) == 1
    request = _FakeAIHandler.requests[0]
    assert request["model"] == "moonshot-v1-8k"
    assert request["messages"][-1]["content"] == "Write a refund reason."
    assert "Authorization" not in str(request)


def test_ai_provider_parses_chat_response(
    fake_server: str, task: SemanticTask, context: GenerationContext
) -> None:
    provider = AIChatProvider(
        ProviderConfig(
            "ai",
            base_url=fake_server,
            model="moonshot-v1-8k",
            api_key_env="EVENTWEAVE_AI_API_KEY",
        )
    )
    os.environ["EVENTWEAVE_AI_API_KEY"] = "test-key"

    asset = provider.generate(task, context)
    assert "fake AI" in asset.text


def test_ai_provider_missing_api_key(
    fake_server: str, task: SemanticTask, context: GenerationContext
) -> None:
    os.environ.pop("EVENTWEAVE_AI_API_KEY", None)
    provider = AIChatProvider(
        ProviderConfig(
            "ai",
            base_url=fake_server,
            model="moonshot-v1-8k",
            api_key_env="EVENTWEAVE_AI_API_KEY",
        )
    )
    with pytest.raises(AIProviderError, match="missing AI API key"):
        provider.generate(task, context)


def test_ai_provider_missing_base_url(task: SemanticTask, context: GenerationContext) -> None:
    os.environ["EVENTWEAVE_AI_API_KEY"] = "test-key"
    os.environ["EVENTWEAVE_AI_MODEL"] = "moonshot-v1-8k"
    provider = AIChatProvider(ProviderConfig("ai"))
    with pytest.raises(AIProviderError, match="missing AI base URL"):
        provider.generate(task, context)


def test_ai_provider_missing_model(task: SemanticTask, context: GenerationContext) -> None:
    os.environ["EVENTWEAVE_AI_API_KEY"] = "test-key"
    os.environ.pop("EVENTWEAVE_AI_MODEL", None)
    provider = AIChatProvider(
        ProviderConfig("ai", base_url="http://127.0.0.1:9999")
    )
    with pytest.raises(AIProviderError, match="missing AI model"):
        provider.generate(task, context)


def test_ai_provider_http_error(
    fake_server: str, task: SemanticTask, context: GenerationContext
) -> None:
    _FakeAIHandler.status = 500
    os.environ["EVENTWEAVE_AI_API_KEY"] = "test-key"
    provider = AIChatProvider(
        ProviderConfig(
            "ai",
            base_url=fake_server,
            model="moonshot-v1-8k",
            api_key_env="EVENTWEAVE_AI_API_KEY",
        )
    )
    with pytest.raises(AIProviderError, match="AI API request failed"):
        provider.generate(task, context)


def test_ai_provider_cache_prevents_repeated_call(
    fake_server: str, tmp_path: Path
) -> None:
    os.environ["EVENTWEAVE_AI_API_KEY"] = "test-key"
    scenario = Scenario(
        id="ecommerce_refund_flow",
        name="E-commerce refund flow",
        domain="ecommerce",
    )
    task = SemanticTask(
        id="refund_reason",
        type="refund.reason",
        prompt="Write a refund reason.",
        valid_for=["refund.requested"],
    )
    event = Event(
        event_id="evt-1",
        scenario_id="ecommerce_refund_flow",
        source_id="order-service",
        event_type="refund.requested",
        event_time="2024-01-01T00:00:00Z",
        entity_refs={},
        attributes={},
        semantic_refs=[],
    )
    provider_config = ProviderConfig(
        "ai",
        base_url=fake_server,
        model="moonshot-v1-8k",
        api_key_env="EVENTWEAVE_AI_API_KEY",
    )
    sidecar = SemanticSidecar(scenario, provider=provider_config, cache=SemanticCache(tmp_path))

    sidecar.generate_task(task, event)
    sidecar.generate_task(task, event)

    assert len(_FakeAIHandler.requests) == 1


@pytest.mark.skipif(
    os.getenv("EVENTWEAVE_RUN_AI_TESTS") != "1",
    reason="Set EVENTWEAVE_RUN_AI_TESTS=1 to run live AI integration tests.",
)
def test_ai_provider_integration() -> None:
    AIProviderConfig.from_options()  # verify env vars are present
    provider = AIChatProvider(ProviderConfig("ai"))
    scenario = Scenario(id="test", name="Test", domain="test")
    task = SemanticTask(id="test", type="test.comment", prompt="Say hello.")
    context = GenerationContext(scenario=scenario, task=task, entities={})
    asset = provider.generate(task, context)
    assert asset.text


def test_ai_provider_retries_on_transient_error_then_succeeds(
    fake_server: str, task: SemanticTask, context: GenerationContext
) -> None:
    _FakeAIHandler.failure_count = 2
    os.environ["EVENTWEAVE_AI_API_KEY"] = "test-key"
    provider = AIChatProvider(
        ProviderConfig(
            "ai",
            base_url=fake_server,
            model="moonshot-v1-8k",
            api_key_env="EVENTWEAVE_AI_API_KEY",
            max_retries=3,
        )
    )

    asset = provider.generate(task, context)
    assert "fake AI" in asset.text
    assert len(_FakeAIHandler.requests) == 3


def test_ai_provider_rejects_malformed_response(
    fake_server: str, task: SemanticTask, context: GenerationContext
) -> None:
    _FakeAIHandler.response_body = json.dumps({"choices": []})
    os.environ["EVENTWEAVE_AI_API_KEY"] = "test-key"
    provider = AIChatProvider(
        ProviderConfig(
            "ai",
            base_url=fake_server,
            model="moonshot-v1-8k",
            api_key_env="EVENTWEAVE_AI_API_KEY",
        )
    )
    with pytest.raises(AIProviderError, match="no choices"):
        provider.generate(task, context)


def test_ai_provider_rejects_truncated_response(
    fake_server: str, task: SemanticTask, context: GenerationContext
) -> None:
    _FakeAIHandler.response_body = json.dumps(
        {"choices": [{"message": {"content": "truncated"}, "finish_reason": "length"}]}
    )
    os.environ["EVENTWEAVE_AI_API_KEY"] = "test-key"
    provider = AIChatProvider(
        ProviderConfig(
            "ai",
            base_url=fake_server,
            model="moonshot-v1-8k",
            api_key_env="EVENTWEAVE_AI_API_KEY",
        )
    )
    with pytest.raises(AIProviderError, match="truncated"):
        provider.generate(task, context)


def test_ai_provider_omits_authorization_when_key_empty(
    fake_server: str, task: SemanticTask, context: GenerationContext
) -> None:
    os.environ["EVENTWEAVE_AI_API_KEY"] = ""
    provider = AIChatProvider(
        ProviderConfig(
            "ai",
            base_url=fake_server,
            model="moonshot-v1-8k",
            api_key_env="EVENTWEAVE_AI_API_KEY",
        )
    )
    provider.generate(task, context)
    assert _FakeAIHandler.auth_headers[-1] is None


def test_ai_provider_marks_asset_pending_when_template_render_fails(
    fake_server: str, context: GenerationContext
) -> None:
    os.environ["EVENTWEAVE_AI_API_KEY"] = "test-key"
    task = SemanticTask(
        id="missing_var",
        type="refund.reason",
        prompt="Reason for {user.name",
        valid_for=["refund.requested"],
    )
    provider = AIChatProvider(
        ProviderConfig(
            "ai",
            base_url=fake_server,
            model="moonshot-v1-8k",
            api_key_env="EVENTWEAVE_AI_API_KEY",
        )
    )

    asset = provider.generate(task, context)

    assert asset.meta.review_status == "pending"
    assert "{user.name" in _FakeAIHandler.requests[-1]["messages"][-1]["content"]


def test_ai_provider_marks_asset_approved_when_template_render_succeeds(
    fake_server: str, context: GenerationContext
) -> None:
    os.environ["EVENTWEAVE_AI_API_KEY"] = "test-key"
    task = SemanticTask(
        id="ok_var",
        type="refund.reason",
        prompt="Reason for scenario {scenario_id}",
        valid_for=["refund.requested"],
    )
    provider = AIChatProvider(
        ProviderConfig(
            "ai",
            base_url=fake_server,
            model="moonshot-v1-8k",
            api_key_env="EVENTWEAVE_AI_API_KEY",
        )
    )

    asset = provider.generate(task, context)

    assert asset.meta.review_status == "approved"
    assert "ecommerce_refund_flow" in _FakeAIHandler.requests[-1]["messages"][-1]["content"]
