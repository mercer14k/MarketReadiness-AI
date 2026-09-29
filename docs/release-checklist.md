# v0.1 release checklist

This is a **local release candidate**. It has not been uploaded to GitHub. Checkmarks below refer to work actually completed during local validation, not intended CI outcomes.

## Implemented and verified natively

- [x] Deterministic 14-market generator and committed dataset; fixed seed and JSON schema.
- [x] BOM allocation, readiness, dated constraints, material gates and binding paths.
- [x] Immutable scenarios and same-dataset comparison.
- [x] Guarded transfers with shared donor-budget conservation.
- [x] Typed API, pagination, idempotency, error paths, health/readiness.
- [x] SQLite persistence, restart behavior and atomic rejected imports.
- [x] Read/write bearer authorization and request MIME/size/origin controls.
- [x] No-LLM core and grounded deterministic briefs.
- [x] Real local Ollama Qwen3-8B structured selection; exact evidence grounding.
- [x] Backend wheel build.
- [x] Frontend production build, typecheck, lint and unit tests.
- [x] Full browser workflow, keyboard drawer dismissal, mobile width check and axe serious/critical accessibility check.
- [x] Real screenshots and reproducible capture instructions.
- [x] Measured benchmarks with hardware, raw JSON/CSV, methodology and limits.
- [x] Runtime dependency advisory audits: no known advisories found at measurement time.
- [x] README, data dictionary, architecture, ADRs, threat model and dependency license inventory.
- [x] GitHub workflow definitions for backend/PostgreSQL, frontend, Compose/browser and audits.

## Required before marking a public container release verified

- [ ] On a Docker host, run `docker compose up --build --wait --wait-timeout 240` from a clean volume.
- [ ] Run `python scripts/smoke.py`, including PostgreSQL-backed persistence.
- [ ] Run the browser suite against `http://localhost:8080` and confirm container security headers.
- [ ] Upload the local source and confirm every GitHub Actions job passes; no CI success is claimed yet.
- [ ] Enable private security reporting, designate maintainer contact and review repository metadata.
- [ ] Review dependency/image licenses, retain notices, and generate image SBOMs before distributing prebuilt containers.
- [ ] Replace placeholder clone links with the final repository URL if adding them; do not add a passing CI badge until CI runs.

Docker Engine was not installed on the authoring machine. Native SQLite and local browser/model success do not prove container or PostgreSQL success. The corresponding executable gates are provided rather than checking those boxes without evidence.

## Publishing suggestions

Repository name: `market-readiness-ai`.

Description: “Open-source material readiness planning for infrastructure deployment: deterministic constraints, guarded transfers, scenario simulation, and grounded local AI.”

Relevant topics: `supply-chain`, `material-requirements-planning`, `infrastructure`, `local-ai`, `ollama`, `fastapi`, `operations-research`, `inventory-management`, `scenario-planning`, `open-source`.

Use the actual portfolio screenshot as the repository preview, and show the Austin → scenario → transfer → brief workflow in a short demo. Share the problem, measured behavior and limitations. Avoid fabricated adoption, ROI, stars, enterprise clients or benchmark claims.
