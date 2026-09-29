# REST API v1

Interactive docs: http://localhost:8000/docs in demo mode. Source dataset contract: `data/schemas/dataset.schema.json`. Responses and mutations use Pydantic models. The generic raw-record page intentionally preserves each selected table's schema.

| Method | Path | Access | Purpose |
|---|---|---|---|
| GET | `/health/live` | public | Process liveness |
| GET | `/health/ready` | public | Database and active snapshot readiness |
| GET | `/api/v1/config` | reader | Runtime mode/version |
| GET | `/api/v1/portfolio` | reader | Baseline scores, requirements, phases, event ledger and timeline |
| GET | `/api/v1/markets/{id}` | reader | Focused market evidence |
| GET | `/api/v1/records/{table}` | reader | Raw record page; `offset`, `limit` 1–500 |
| GET | `/api/v1/validation-reports` | reader | Validation history; paginated by offset/limit |
| GET | `/api/v1/scenarios` | reader | Scenario summaries; paginated by offset/limit |
| GET | `/api/v1/scenarios/{id}` | reader | Immutable scenario result |
| GET | `/api/v1/compare?right={id}&left={id}` | reader | Same-dataset comparison; omit left for active baseline |
| GET | `/api/v1/forecast` | reader | Forecasts and per-series backtest errors |
| GET | `/api/v1/exports/readiness.csv` | reader | Sanitized CSV export |
| POST | `/api/v1/transfers` | reader, computed query | Guarded recommendations; no state change |
| POST | `/api/v1/briefs` | reader, computed query | Daily/weekly grounded brief; no business state change |
| POST | `/api/v1/scenarios` | writer | Persist an immutable scenario |
| POST | `/api/v1/imports` | writer | Validate and atomically activate a new dataset |

All POST requests use `Content-Type: application/json`. Persisted mutations require `Idempotency-Key` (8–128 safe identifier characters). The API fingerprints the operation and rejects conflicting reuse with HTTP 409. Dataset IDs are immutable; an updated snapshot needs a new ID.

An invalid-but-parseable dataset returns HTTP 200 with `accepted: false` and a stored validation report. Malformed JSON returns 400; wrong MIME 415; oversized bodies 413; invalid operation/request 422; missing objects 404. This distinction lets callers inspect all schema findings without pretending the import was activated.

```json
{"error":{"code":"validation_error","message":"Request validation failed","trace_id":"…","details":[{"field":"body.accelerate_days","message":"…"}]}}
```

Responses include `X-Trace-ID`. The trace is generated server-side. Unknown exception details are never returned. Some edge proxy errors (for example Nginx's own body limit) are proxy responses and may not carry the application's JSON envelope.

### Scenario

```json
{"name":"PO slip","po_delays":{"po-m00-00-fiber":14},"accelerate_days":5,"market_ids":["m00-00"],"horizon_days":90}
```

`market_ids` scopes acceleration only; PO delays target their explicit IDs. Empty market IDs applies acceleration to all markets. Acceleration clamps dates at the dataset as-of date.

### Transfer query

```json
{"run_id":null,"guardrails":{"transit_days":3,"reserve_multiplier":1,"min_donor_readiness":100,"same_region_only":false,"max_transfer":100000}}
```

Transfers can use an archived scenario's own source dataset. They are not persisted as inventory movements.

### Import

Send the JSON snapshot directly; there is no multipart filename or executable connector:

```bash
curl -X POST http://localhost:8000/api/v1/imports \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: import-snapshot-001' \
  --data-binary @data/sample/portfolio.json
```

In secured mode, add `Authorization: Bearer <write token>`. The public UI can accept a token in its connection form; it remains in memory only.
