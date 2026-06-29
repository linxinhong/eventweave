# AI Semantic Sidecar

The AI Semantic Sidecar generates human-like text assets for EventWeave scenarios
without touching the runtime hot path. It is **AI-assisted, not AI-dependent**:
the default providers work offline and require no API keys.

## What it does

- Reads a compiled runtime plan (`scenario.json`, `semantic_tasks.json`, `event_plan.jsonl`).
- Generates `SemanticAsset` objects such as refund reasons, ticket descriptions,
  alert summaries, or user comments.
- Caches generated assets so they can be reused, reviewed, and audited.
- Validates every asset against its task and the event it belongs to.
- Writes a `semantic_pool.json` that the runtime can inject into events.

## Architecture

```text
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Runtime Plan   │────▶│ Semantic Sidecar │────▶│ semantic_pool   │
│  + semantic_    │     │ - provider       │     │ .json           │
│    tasks.json   │     │ - cache          │     │                 │
└─────────────────┘     │ - validator      │     └─────────────────┘
                        └──────────────────┘                │
                                                            ▼
                                                  ┌─────────────────┐
                                                  │ event_plan with │
                                                  │ semantic_refs   │
                                                  └─────────────────┘
```

## Providers

Providers implement the `Provider` abstract base class. The sidecar ships with
two built-in providers:

### `mock` (default)

Returns deterministic placeholder text. Useful for CI, testing, and demos.

```bash
eventweave semantic generate dist/ecommerce_refund_flow_semantic --provider mock
```

### `template`

Renders templates using scenario variables such as `{user.name}` or `{order.id}`.
No LLM is called.

```bash
eventweave semantic generate dist/ecommerce_refund_flow_semantic --provider template
```

### `ai`

Calls any Chat Completions compatible HTTP API. This works with Kimi,
DeepSeek, Qwen-compatible gateways, and local model servers such as Ollama's
OpenAI-compatible endpoint.

AI calls are optional: `mock` remains the default. The runtime never calls an
AI API; generation only happens during `eventweave semantic generate`. All AI
outputs are cached and validated before being written to `semantic_pool.json`.

Configure via environment variables:

```bash
export EVENTWEAVE_AI_BASE_URL=https://api.moonshot.cn/v1
export EVENTWEAVE_AI_API_KEY=your-kimi-api-key
export EVENTWEAVE_AI_MODEL=moonshot-v1-8k

eventweave semantic generate dist/ecommerce_refund_flow_semantic --provider ai
```

Or use CLI options:

```bash
eventweave semantic generate dist/ecommerce_refund_flow_semantic \
  --provider ai \
  --base-url https://api.moonshot.cn/v1 \
  --model moonshot-v1-8k \
  --api-key-env EVENTWEAVE_AI_API_KEY \
  --timeout 60 \
  --max-retries 3
```

`--api-key-env` lets you use a custom environment variable name. The API key is
never accepted as a CLI argument, so it cannot leak into shell history.

You can also set `--max-tokens` and `--temperature` to control the model output.

### Robustness

The `ai` provider:

- Retries transient failures (HTTP 429, 5xx, network errors) with exponential backoff.
- Validates the Chat Completions response shape before use.
- Raises a clear error if the response is truncated (`finish_reason="length"`).
- Omits the `Authorization` header when the API key is empty, so local servers
  like Ollama work without a dummy key.

Local model example with Ollama:

```bash
export EVENTWEAVE_AI_BASE_URL=http://127.0.0.1:11434/v1
export EVENTWEAVE_AI_API_KEY=dummy
export EVENTWEAVE_AI_MODEL=qwen2.5:7b

eventweave semantic generate dist/ecommerce_refund_flow_semantic --provider ai
```

### Custom provider

Register a custom provider by subclassing `Provider`:

```python
from eventweave.ai.provider import Provider, GenerationContext
from eventweave.core.semantic import SemanticAsset, SemanticAssetMeta, SemanticTask

class MyProvider(Provider):
    @property
    def provider_type(self) -> str:
        return "my_provider"

    def generate(self, task: SemanticTask, context: GenerationContext) -> SemanticAsset:
        # Call your LLM here.
        return SemanticAsset(
            id=f"{task.id}-my",
            type=task.type,
            text="Generated text",
            meta=SemanticAssetMeta(provider=self.provider_type, source_task=task.id),
        )
```

Then register it:

```python
from eventweave.ai.sidecar import register_provider

register_provider("my_provider", MyProvider)
```

## Defining semantic tasks

Semantic tasks can be declared at the scenario level:

```yaml
id: ecommerce_refund_flow
domain: ecommerce
# ...
semantic_tasks:
  - id: refund_reason
    type: refund.reason
    template: "Customer {user.name} requests refund for order {order.id}: {reason}."
    variables: [user.name, order.id, reason]
    valid_for: [refund.requested]
    count: 1
```

Or inline on timeline items:

```yaml
timeline:
  - id: request_refund
    event: refund.requested
    semantic:
      type: refund.reason
      prompt: "Write a short refund reason in Chinese."
```

`valid_for` restricts the task to specific event types. `count` controls how
many variants are generated per event.

## CLI usage

Generate semantic assets for a compiled plan:

```bash
eventweave compile examples/ecommerce/refund_with_semantic.yaml -o dist
eventweave semantic generate dist/ecommerce_refund_flow_semantic --provider template
```

Inspect the generated pool:

```bash
eventweave semantic inspect dist/ecommerce_refund_flow_semantic/semantic_pool.json
```

Force regeneration and ignore the cache:

```bash
eventweave semantic generate dist/ecommerce_refund_flow_semantic --provider template --force
```

Use a custom cache directory:

```bash
eventweave semantic generate dist/ecommerce_refund_flow_semantic --cache-dir ./semantic_cache
```

## Cache

Generated assets are cached under the plan directory by default
(`dist/<scenario>/.semantic_cache`). The cache key includes the provider type,
scenario id, task id, and event id. Delete the cache directory to regenerate
everything, or use `--force`.

## Validation

Every generated asset is validated against:

- type matches the task type
- non-empty text
- text length within `max_length` (default 4096)
- event type is in `task.valid_for` when applicable

Invalid assets raise `ValidationError` and stop generation so problems are caught
early.

## Semantic refs in event plan

During compilation, EventWeave attaches placeholder `semantic_refs` to events:

```json
{
  "event_id": "evt-ecommerce-refund-flow-001-003",
  "event_type": "refund.requested",
  "semantic_refs": ["semantic://refund_reason"]
}
```

After `semantic generate`, these placeholders can be resolved to concrete asset
ids from `semantic_pool.json` by a runtime or post-processor.

## Safety and privacy

- AI generation is optional. The default `mock` provider works without any
  external service.
- The runtime never calls AI APIs; AI is only used during `semantic generate`.
- AI outputs are cached locally and validated before use.
- Do not send sensitive real data to external AI APIs.
- API keys are read from environment variables only and never accepted as CLI
  arguments.

## Testing without an LLM

All tests pass without API keys because the default `mock` and `template`
providers are deterministic and offline. See `tests/ai/` for examples.

To run optional live AI integration tests, set:

```bash
export EVENTWEAVE_AI_BASE_URL=https://api.moonshot.cn/v1
export EVENTWEAVE_AI_API_KEY=your-kimi-api-key
export EVENTWEAVE_AI_MODEL=moonshot-v1-8k
EVENTWEAVE_RUN_AI_TESTS=1 pytest tests/ai/test_ai_provider.py
```
