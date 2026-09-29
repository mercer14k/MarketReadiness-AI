# Measured benchmark example

Generated: 2026-09-29T01:24:11.869981+00:00. Hardware: **Apple M5**, macOS-26.6.2-arm64-arm-64bit, Python 3.12.14.

Configuration: seed 42; 90-day horizon; mrp-1.0; 3 warm runs. LLM: qwen3:8b; actual briefing mode: **local-llm**.

| Markets | Source records | Median (ms) | Maximum (ms) | Python peak allocated (MiB) |
|---:|---:|---:|---:|---:|
| 14 | 5,024 | 4.1 | 14.0 | 3.0 |

Timing covers planning and result hashing; excludes file parsing, database, forecast, HTTP, UI and LLM. Memory is a separate tracemalloc pass and excludes native allocations. Maximum is not a p95 claim.

| Evaluation | Measured result |
|---|---|
| Constraint dates / no-constraint classifications | 14/14 exact synthetic fixture matches |
| Constraint date MAE | 0.0 days on 5 matched constrained markets |
| Portfolio readiness absolute error | 0.00 percentage points |
| Consumption forecast WAPE | 9.40% on 1176 held-out observations |
| Transfer timing / safety-floor checks | 6/6 recommendations pass |
| Explanation evidence equality | 8/8 statements grounded |

These are synthetic regression and diagnostic results, **not real-world accuracy claims**. Grounding is guaranteed by exact evidence rendering, not a measure of model judgment. An abstaining model produces zero claims; zero claims are never reported as 100% success. See results.json for actual runtime/configuration, validation failures, tokens and latency. Forecast WAPE pools units and is dominated by high-volume fiber/conduit; use per-material API metrics when assessing individual series.
