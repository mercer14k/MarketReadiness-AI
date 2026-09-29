# Evaluation and performance

Run after installing the Python project:

```bash
python -m marketreadiness.evaluation.benchmark
```

The command generates JSON, CSV and Markdown under `artifacts/benchmark/`. Add `--scale 50 --repeats 10` for a larger run, or `--model qwen3:4b --ollama-url http://localhost:11434` for local AI telemetry. All data generation uses seed 42. The committed examples use their own explicit hardware/model configurations.

## What is measured

| Measure | Method | Interpretation |
|---|---|---|
| Constraint accuracy | Compare all 14 market dates/nulls with hand-reviewed synthetic oracle | Regression correctness; not real-world forecasting validity |
| Constraint date MAE | Absolute error on dated cases matched by both result and oracle | Always read with exact-match count; misses are not hidden as zero error |
| Readiness accuracy | Fixed oracle plus exact arithmetic unit tests | Checks formula and conservation semantics |
| Forecast accuracy | Train on first 42 observations; hold out last 14 per series | Weekday-mean WAPE and MAE; no hold-out rows in training |
| Transfer validity | Receipt by need date and donor floor; unit tests also enforce shared stock conservation | Validity, not cost optimality |
| Explanation grounding | Exact selected evidence equality and source IDs | Claim support, not model salience or writing quality |
| Runtime | One warm-up then repeated `plan()` runs | Excludes parsing, persistence, forecast, network, UI, LLM |
| Memory | Separate `tracemalloc` pass | Python allocations only, not RSS or native/model memory |

Model token/latency/version metadata is in JSON. Model failure and abstention are reported as modes; no fabricated accuracy is substituted. The no-LLM benchmark is the default. Model throughput depends on hardware, quantization, cache state and runtime; the example is one run, not a statistically powered comparison.

Forecast errors mix meters and individual components when pooled; portfolio WAPE is dominated by fiber and conduit. Use the per-market/material endpoint to inspect each unit separately. The synthetic generator has a weekly pattern, making weekday-mean a reasonable baseline rather than proof of superiority over more advanced models.

## Tests

```bash
pytest --cov=marketreadiness --cov=apps.api --cov-report=term-missing
cd apps/web
pnpm lint
pnpm typecheck
pnpm test
pnpm build
# Start the application first, then:
pnpm exec playwright install chromium
pnpm test:e2e
```

The backend suite uses isolated SQLite databases by default. Set `TEST_DATABASE_URL` to a dedicated disposable PostgreSQL database for integration validation. Never point tests at an operational database. CI provisions PostgreSQL and separately builds and starts Docker Compose.

The browser suite verifies portfolio results, an evidence drawer, phase delays, scenario persistence/comparison, transfers, grounded briefing, forecasts, filtering, rejected imports, unchanged baseline, responsive layout and serious/critical axe accessibility findings. It captures real screenshots in `docs/images/`.

## Evidence and boundaries

- [Native deterministic measurement](benchmarks/native-no-llm/summary.md)
- [Ollama / Qwen3-8B measurement](benchmarks/local-qwen3-8b/summary.md)
- [Release verification status](release-checklist.md)

Native tests and actual local AI were run on the development machine. Docker Engine was unavailable there; the Compose and PostgreSQL service jobs are supplied as executable release gates, not represented as already passed. GitHub Actions has not run because the deliverable is local and has not been published.
