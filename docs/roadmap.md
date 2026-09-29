# Roadmap: the next five technically meaningful improvements

The implemented core is deterministic planning, snapshot persistence, versioned API, analytical UI, guarded transfers, optional grounded local briefing and reproducible evaluation. Stretch work should begin only after the container release gates pass.

## 1. Probabilistic supplier readiness

Fit lead-time and commitment-slippage distributions on appropriately licensed historical events. Add rolling-origin evaluation, interval coverage, calibration and bias by supplier/material. Gate release on comparison against deterministic and empirical baselines. Expose uncertainty separately from coverage scores.

## 2. Network-flow transfer optimization

Replace the greedy advisory allocator with min-cost flow subject to time-expanded supply, freight capacity, lane transit times, donor risk floors and service-level targets. Prove conservation and feasibility, publish optimality gaps and sensitivity to uncertain transit. Preserve an inspectable feasible fallback.

## 3. Incremental, multi-cohort ingestion

Introduce program/project/cohort entities, normalized event records and schema migrations. Add idempotent source adapters, reconciliation totals, late-arriving event handling and replay. Preserve an immutable evaluation snapshot for every result. Optional proprietary adapters must stay outside the default path.

## 4. Work-package execution model

Model daily installation demand, labor calendars, substitutions, scrap/yield, partial completions and kitting. Define how expected usage replaces scheduled demand without double counting. Validate on small independently solved examples before measuring larger instances.

## 5. Shared deployment engineering

Add OIDC, per-market permissions, audit actors, background compute jobs, rate limiting, database migrations, backup/restore exercises and latency/error SLOs. Add authenticated-browser accessibility and security tests. Publish image SBOMs and signed release artifacts. Do not claim multi-tenant isolation until it is tested.
