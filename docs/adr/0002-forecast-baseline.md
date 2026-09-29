# ADR 0002: Weekday mean instead of StatsForecast for the first core

Status: accepted.

Use a small, explicit weekday-mean statistical forecast with Polars grouping instead of introducing StatsForecast in v0.1. The seeded usage has a weekly pattern and only 56 observations per series; an interpretable baseline makes leakage, hold-out policy and edge cases inspectable. Readiness itself uses contractual supply and scheduled BOM demand.

Consequence: fewer numerical dependencies and deterministic behavior, but no intervals, trend model, intermittent-demand model, calendar exceptions or automatic model selection. Forecast outputs are diagnostic and not added to the same scheduled BOM requirements. A rolling-origin comparison with seasonal-naive, Croston and ETS is a next-step improvement before claiming better predictive accuracy.
