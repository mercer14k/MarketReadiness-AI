# Architecture

MarketReadiness is a single-program, local-first planning application. HTTP handlers validate and dispatch; the domain package owns numerical calculations. The React application renders API responses and performs no inventory allocation.

## Layers

| Layer | Responsibilities | Does not own |
|---|---|---|
| `domain` | Integer BOM explosion, finite supply allocation, dependency scheduling, transfer guardrails, forecasts | HTTP, SQL, LLM calls |
| `data` | Seed generator, cross-record validation, immutable snapshots, active pointer, retry ledger | Business KPIs |
| `services` | Imports, scenarios, comparisons, evidence orchestration, export | UI state |
| `ai` | Local runtime protocol, schema validation, evidence selection, exact rendering | Numbers, SQL, commands, mutations |
| `apps/api` | Versioned routes, authorization, bounded requests, error envelopes, trace IDs | Planning logic |
| `apps/web` | Search, filtering, drill-downs, scenario controls, charts, accessible states | Readiness calculations |
| `evaluation` | Fixed-oracle correctness, held-out forecast errors, timing and memory evidence | Production learning |

See [the portable Mermaid source](architecture.mmd) and [editable diagram specification](architecture.spec.json). The diagram has passed static skill validation; GitHub rendering is not claimed as locally verified.

## Planning semantics

1. Each market describes one home cohort across its build phases. BOM quantities are `ceil(homes × units_per_home)`, using decimal arithmetic before integer rounding. Duplicate material BOM lines sum.
2. Inventory is an **as-of snapshot**. Available stock is physical quantity minus reserved minus quarantined. Historical consumption is already reflected in that snapshot and is not subtracted again.
3. Open PO supply is ordered quantity minus received quantity. The latest commitment by `(updated_at, id)` controls confirmation. Its receipt date is the later of PO ETA and commitment promise. Cancelled, closed, fully received, unconfirmed and overdue receipts are excluded. Scenario delays are explicit hypothetical changes.
4. Requirements are sorted by due date, market priority, and stable plan ID. Supply is reserved FIFO by date then stable supply ID, including later receipts. A later requirement cannot reuse stock already allocated to an earlier one. This conservative reservation policy can prevent later work from leapfrogging earlier commitments.
5. Requirement score is `100 × on_time_allocated / required`. Family, phase and market scores take the lowest applicable requirement score. Portfolio score weights market bottlenecks by cohort homes; raw quantities from different units are never summed into a coverage score.
6. Earliest feasible phase start is the latest of planned start, its material-ready dates, and predecessor finish plus one day. Missing sufficient confirmed supply gives a null completion, not an invented date. Durations use inclusive calendar days.
7. Earliest constraint is the first planned phase start that cannot be met. The binding critical path starts at the limiting material requirement or scheduled release, then follows controlling dependencies. Non-binding predecessors with slack do not appear on that path; the phase sequence remains separately visible.
8. The ledger is event-based. It includes the as-of day, receipt days, demand days and horizon end. Between events, the balance is constant. Negative projected balances expose shortages. Weekly timeline points include the exact horizon end.

Readiness is a material-coverage score, **not a probability**. A schedule dependency can create an at-risk market even when material coverage is 100%. `Watch` is reserved by the response contract; this conservative policy ordinarily produces Ready or At risk.

## Transfer proof obligations

A recommendation must use current stock, reach the recipient by its requirement date, and leave the donor at or above `ceil(safety_stock × reserve_multiplier)` at **every event through the scenario horizon**. The donor must satisfy the minimum score and have a higher score than the recipient. Same-region restrictions, per-transfer limits and transit days are configurable.

The planner subtracts earlier recommendations from a shared donor budget. It cannot spend the same units twice. Transfers remain advisory: late POs are not cancelled, and excess supply after recovery is not optimized. Fixed transit time does not include freight capacity, routing cost or actual carrier calendars.

## Persistence and concurrency

PostgreSQL stores validated immutable JSON documents, with a separate active-dataset pointer and unique idempotency keys. SQLAlchemy emits parameterized statements. Initial schema creation is version 1; there are no subsequent migrations yet.

An import transaction writes its report, accepted snapshot, active pointer and retry response atomically. Errors reject the full snapshot. A stable dataset ID cannot be reused for different content; use a new version ID. Scenarios retain their source dataset and never mutate inventory. Cross-dataset comparison is rejected. PostgreSQL advisory transaction locking serializes writes; unique constraints resolve retry races. This intentionally favors correctness over write throughput.

The API uses a non-superuser writer and a distinct read-only PostgreSQL role. Native development can use SQLite with the same schema. SQLite does not provide PostgreSQL's server-enforced reader role or equivalent multi-writer guarantees.

## Operational boundary

Default Compose ports bind only to loopback. There is no external integration, scheduler, SaaS account, training service, or cloud AI dependency. The app reads immutable snapshots rather than continuously reconciling an ERP event stream. Memory usage scales with dataset size; it does not claim warehouse-scale streaming ingestion.
