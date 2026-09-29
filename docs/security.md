# Security and threat model

## Scope and trust boundaries

This is a local, single-program planning demonstrator. Default demo mode requires no credentials and must remain bound to loopback. The deployed service is **not** a multi-tenant SaaS. No enterprise compliance certification is claimed.

Assets: source snapshots, computed scenarios, API credentials (when configured), model prompts, and import integrity. Boundaries: browser → API; API → reader/writer database roles; external dataset → typed validator; verified facts → optional local model → schema validator.

| Threat | Implemented control | Remaining work for shared deployment |
|---|---|---|
| Unauthorized reads/writes | Central router dependencies; distinct read/write bearer tokens in secured mode; fail closed on weak/missing token configuration | Identity provider, scoped users, per-market ACLs, rotation |
| Malicious imports / mass assignment | 20 MiB streaming body cap; JSON MIME only; bounded Pydantic fields; extra fields forbidden; full atomic rejection | Rate limits, queueing, workload quotas, malware scanning if binary formats are ever added |
| File traversal | No client filename is accepted or saved; JSON goes to typed database snapshots | Keep this boundary for future connectors |
| SQL injection | SQLAlchemy parameterized queries; fixed internal health/advisory-lock SQL | Continue parameterization in future query features |
| Spreadsheet formula injection | CSV export neutralizes leading formula characters in imported names | Confirm downstream spreadsheet behavior |
| Cross-site local requests | No permissive CORS; demo-mode origin allowlist; JSON-only POST; no cookie auth | TLS and trusted reverse proxy for any external exposure |
| XSS / model HTML | React escaping; no raw HTML rendering; CSP and browser headers in Nginx | Browser regression tests with untrusted labels |
| Prompt injection / hallucination | Model selects allowlisted evidence IDs; no model text rendered; contradiction checks and fallback; no tools | Evaluate salience and prompt-injection resistance as adapters grow |
| SSRF / cloud leakage | Local runtime host allowlist; redirects/proxies disabled; downloaded-model check; no cloud model names; Ollama cloud disabled in Compose | Network isolation and egress policy on shared hosts |
| Corrupt retries / partial data | Transactional import, immutable snapshot IDs, unique request fingerprint, PostgreSQL write lock | Retention policy and distributed job control |
| Database privilege escalation | Non-superuser writer; SELECT-only reader with read-only transactions; no exposed DB port | Secret injection and least-privilege migration identity |
| Dependency compromise | Exact Python locks and pnpm lock; allowlisted esbuild install script, disabled Scarf install telemetry; pip-audit/pnpm audit CI | Image SBOM scanning, signed releases, pinned action/image digests |
| Resource exhaustion | Bounded inputs, Uvicorn concurrency limit, runtime timeout, one retry | Per-principal rate limiting and asynchronous job admission |

## Demo credentials and production mode

Compose contains clearly named **public demo-only** PostgreSQL credentials on an isolated internal network. They are not secrets and must never be reused elsewhere. Actual tokens, customer credentials and `.env` files are excluded from source control. Replace database identities/passwords and use secret injection before any shared deployment.

Set `APP_MODE=secured`, generate distinct cryptographically random `READ_API_TOKEN` and `WRITE_API_TOKEN` values of at least 32 characters, and restrict `ALLOWED_HOSTS`. Readers can fetch data and request non-persistent calculations. Only writers can import a new active snapshot or save a scenario. The UI stores an entered token only in memory; refresh clears it. API docs are disabled in secured mode.

Database roles are initialized only for a fresh PostgreSQL volume. Changing `.env` or SQL does not rotate existing database credentials. Use a controlled database migration/rotation procedure. SQLite native mode has no separate server-side reader identity.

## Logging and privacy

Structured request logs contain method, path, status, latency and a generated trace ID, never headers or body content. Model telemetry contains evidence IDs and configuration, not raw output or hidden reasoning. Synthetic data contains no customer records. A secured installation still returns source provenance to authorized readers; classify that data before adapting it to an actual program.

No arbitrary shell or SQL is model-generated or executed. No model has a state-changing tool. Transfers are recommendations only. Forecasts and brief generation never update inventory.

## Validation status

Native backend, frontend, browser, model-failure and known-advisory checks are documented in the release checklist. Those checks do not constitute a full penetration test. TLS is intentionally outside the local demo boundary; put a properly configured gateway in front of any shared installation and retest the whole trust model.
