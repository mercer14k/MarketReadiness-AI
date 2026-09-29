# Local AI design

All core workflows operate with `LLM_PROVIDER=none`. The briefing still produces useful deterministic text. No runtime downloads a model implicitly, and no proprietary AI service is implemented.

## Evidence-bounded briefing

The planning service builds a finite catalog of exact, pre-rendered facts. The local model returns only:

```json
{"evidence_ids":["run-…:portfolio","req-plan-…-fiber"],"posture":"attention"}
```

The application validates the JSON schema, allowed IDs, uniqueness, non-empty claims, and consistency of posture with calculated risk. It then renders the selected facts verbatim from the catalog. The model cannot introduce numerical values, new narrative claims, links, or executable text. Daily format caps the result at four statements; weekly caps it at eight. Both describe the same configured planning horizon.

This is a deliberate tradeoff: wording is templated, while salience and ordering can be model-selected. It provides a strong grounding invariant but does not prove that the model chose the most useful evidence. A future qualitative ranking evaluation should assess that separately.

## Runtime abstraction

`LocalRuntime` is a Python protocol: `select(evidence) -> (BriefSelection, telemetry)`. Business logic depends only on that protocol. `OllamaRuntime` is the first concrete implementation. A llama.cpp or vLLM adapter can implement the same interface later; they are not claimed as shipped integrations.

The adapter restricts outbound connections to configured local hosts, refuses cloud model names and URL credentials, disables environment proxy inheritance and redirects, checks that the model is downloaded, sends a JSON Schema, and uses temperature 0 / seed 42. The Compose runtime sets `OLLAMA_NO_CLOUD=1`. Model licenses remain distinct from the application license.

The default downloadable option is `qwen3:4b`; the measured local run used an already-installed **qwen3:8b Q4_K_M**, with digest and runtime version in the committed benchmark. Qwen3 model cards declare Apache-2.0: [4B](https://huggingface.co/Qwen/Qwen3-4B), [8B](https://huggingface.co/Qwen/Qwen3-8B). Review the exact model card and redistribution terms when replacing the model. Weights are not included in this repository.

## Failure and abstention

No evidence means abstention before any model call. A valid model abstention emits no statements. Runtime timeout, missing model, malformed JSON, unknown IDs, duplicate claims, and contradictory posture trigger one bounded retry, then an explicitly labeled deterministic fallback. Failure cannot change a planning result or persisted inventory.

The adapter requests no chain-of-thought. Thinking fields, when present, are not inspected, retained, or displayed. Evidence text is untrusted data; the system instruction explicitly disallows treating it as instructions. Exact fact rendering is the enforcement boundary, not prompt wording alone. There are no model tools, shell commands, arbitrary SQL, or write actions.

## Telemetry

Brief output and structured logs contain episode ID, source dataset/run IDs, algorithm/prompt version, provider, requested/reported model, model digest, runtime version, quantization metadata, options, seed, input evidence IDs, latency, retry count, validation failures, error type, token counts when available, and an empty tool-call list. HTTP requests carry separate trace IDs. Request bodies, tokens, raw model output and reasoning are not logged.

```bash
# Native runtime; once downloaded this works without internet.
ollama pull qwen3:4b
# Stop any existing listener before starting a differently configured server.
OLLAMA_NO_CLOUD=1 ollama serve
LLM_PROVIDER=ollama LLM_MODEL=qwen3:4b OLLAMA_BASE_URL=http://localhost:11434 \
  python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
```

With Docker: set `LLM_PROVIDER=ollama` in `.env`, run `docker compose --profile ai up --build -d`, then `docker compose exec ollama ollama pull qwen3:4b`. The API is usable before the download completes; the brief labels its fallback. On Apple Silicon, native Ollama can use Metal; the default container is a portable CPU path and may be slower.

Reference: [Ollama structured-output API](https://github.com/ollama/ollama/blob/main/docs/capabilities/structured-outputs.mdx).
