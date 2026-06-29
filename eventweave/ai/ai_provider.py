"""Generic AI chat provider for semantic asset generation."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from eventweave.ai.ai_config import AIProviderConfig, AIProviderError
from eventweave.ai.provider import GenerationContext, Provider
from eventweave.core.semantic import SemanticAsset, SemanticAssetMeta, SemanticTask


class _ChatCompletionMessage(BaseModel):
    content: str


class _ChatCompletionChoice(BaseModel):
    message: _ChatCompletionMessage
    finish_reason: str | None = Field(default=None)


class ChatCompletionResponse(BaseModel):
    """Minimal validated shape of a Chat Completions response."""

    choices: list[_ChatCompletionChoice] = Field(default_factory=list)


class AIChatProvider(Provider):
    """Provider that calls a Chat Completions compatible HTTP API.

    Works with any endpoint implementing the Chat Completions protocol,
    including Kimi, DeepSeek, Qwen-compatible gateways, and local model
    servers such as Ollama's OpenAI-compatible endpoint.
    """

    @property
    def provider_type(self) -> str:
        return "ai"

    def generate(
        self,
        task: SemanticTask,
        context: GenerationContext,
    ) -> SemanticAsset:
        config = AIProviderConfig.from_options(
            base_url=self.config.options.get("base_url"),
            model=self.config.options.get("model"),
            api_key_env=self.config.options.get("api_key_env", "EVENTWEAVE_AI_API_KEY"),
            timeout=self.config.options.get("timeout"),
            max_retries=self.config.options.get("max_retries"),
            max_tokens=self.config.options.get("max_tokens"),
            temperature=self.config.options.get("temperature"),
        )
        messages, render_ok = self._build_messages(task, context)
        response = self._chat_completion(config, messages)
        text = self._extract_text(response)

        review_status = "approved" if render_ok else "pending"
        return SemanticAsset(
            id=f"{task.id}-ai",
            type=task.type,
            text=text,
            valid_for=list(task.valid_for),
            meta=SemanticAssetMeta(
                provider=self.provider_type,
                source_task=task.id,
                source_event=context.event.event_id if context.event else None,
                review_status=review_status,
            ),
        )

    def _build_messages(
        self,
        task: SemanticTask,
        context: GenerationContext,
    ) -> tuple[list[dict[str, str]], bool]:
        system = (
            "You are generating synthetic event content for a scenario simulation. "
            "Produce a short, realistic text asset. "
            "Do not include explanations or markdown formatting."
        )
        user_prompt, render_ok = self._render_template(task.prompt or task.template, context)
        if not user_prompt:
            user_prompt = f"Generate a {task.type} asset for task {task.id}."
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ], render_ok

    def _chat_completion(
        self,
        config: AIProviderConfig,
        messages: list[dict[str, str]],
    ) -> ChatCompletionResponse:
        body: dict[str, Any] = {
            "model": config.model,
            "messages": messages,
        }
        if config.max_tokens is not None:
            body["max_tokens"] = config.max_tokens
        if config.temperature is not None:
            body["temperature"] = config.temperature

        url = f"{config.base_url}/chat/completions"
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
        request = urllib.request.Request(
            url,
            data=payload,
            headers=headers,
            method="POST",
        )

        last_error: Exception | None = None
        for attempt in range(max(config.max_retries, 0) + 1):
            try:
                with urllib.request.urlopen(request, timeout=config.timeout) as response:
                    response_data: dict[str, Any] = json.loads(response.read().decode("utf-8"))
                    return self._parse_response(response_data)
            except urllib.error.HTTPError as exc:
                if exc.code in (429, 500, 502, 503, 504) and attempt < config.max_retries:
                    last_error = exc
                    time.sleep(self._backoff(attempt))
                    continue
                raise AIProviderError(
                    f"AI API request failed: {exc.code} {exc.reason}"
                ) from exc
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                if attempt < config.max_retries:
                    last_error = exc
                    time.sleep(self._backoff(attempt))
                    continue
                raise AIProviderError(f"AI API request failed: {exc}") from exc
            except json.JSONDecodeError as exc:
                raise AIProviderError(
                    f"AI API returned invalid JSON: {exc}"
                ) from exc

        raise AIProviderError(
            f"AI API request failed after {config.max_retries} retries"
        ) from last_error

    @staticmethod
    def _backoff(attempt: int) -> float:
        """Exponential backoff with a small jitter cap."""
        return float(min(2**attempt, 30.0))

    def _parse_response(self, response_data: dict[str, Any]) -> ChatCompletionResponse:
        try:
            response = ChatCompletionResponse.model_validate(response_data)
        except ValidationError as exc:
            raise AIProviderError(
                f"unexpected AI API response format: {exc}"
            ) from exc

        if not response.choices:
            raise AIProviderError("AI API response has no choices")

        choice = response.choices[0]
        if choice.finish_reason == "length":
            raise AIProviderError(
                "AI response was truncated (finish_reason='length'); "
                "try increasing max_tokens or shortening the prompt"
            )

        return response

    def _extract_text(self, response: ChatCompletionResponse) -> str:
        return response.choices[0].message.content.strip()
