"""Generic AI chat provider for semantic asset generation."""

from __future__ import annotations

import json
import urllib.request
from typing import Any

from eventweave.ai.ai_config import AIProviderConfig, AIProviderError
from eventweave.ai.provider import GenerationContext, Provider
from eventweave.core.semantic import SemanticAsset, SemanticAssetMeta, SemanticTask


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
        )
        messages = self._build_messages(task, context)
        response = self._chat_completion(config, messages)
        text = self._extract_text(response)

        return SemanticAsset(
            id=f"{task.id}-ai",
            type=task.type,
            text=text,
            valid_for=list(task.valid_for),
            meta=SemanticAssetMeta(
                provider=self.provider_type,
                source_task=task.id,
                source_event=context.event.event_id if context.event else None,
            ),
        )

    def _build_messages(
        self,
        task: SemanticTask,
        context: GenerationContext,
    ) -> list[dict[str, str]]:
        system = (
            "You are generating synthetic event content for a scenario simulation. "
            "Produce a short, realistic text asset. "
            "Do not include explanations or markdown formatting."
        )
        user_prompt = self._render_template(task.prompt or task.template, context)
        if not user_prompt:
            user_prompt = f"Generate a {task.type} asset for task {task.id}."
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ]

    def _chat_completion(
        self,
        config: AIProviderConfig,
        messages: list[dict[str, str]],
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": config.model,
            "messages": messages,
        }

        url = f"{config.base_url}/chat/completions"
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=config.timeout) as response:
                response_data: dict[str, Any] = json.loads(response.read().decode("utf-8"))
                return response_data
        except urllib.error.HTTPError as exc:
            raise AIProviderError(
                f"AI API request failed: {exc.code} {exc.reason}"
            ) from exc
        except urllib.error.URLError as exc:
            raise AIProviderError(f"AI API request failed: {exc.reason}") from exc

    def _extract_text(self, response: dict[str, Any]) -> str:
        try:
            return str(response["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise AIProviderError(
                "unexpected AI API response format: missing choices[0].message.content"
            ) from exc
