# Native development

Use Python 3.12 or later and Node.js 24 with pnpm 11.25.0. The measured environment used Python 3.12.14 and Node 24.19.0. Node and Python are open source; no vendor account is needed. A separate PostgreSQL installation is optional for native development.

## macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pip install --no-deps -e .
cp .env.example .env
python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
npm install --global pnpm@11.25.0
cd apps/web
pnpm install --frozen-lockfile
pnpm dev
```

Open http://127.0.0.1:5173. The frontend proxies `/api` to port 8000. SQLite persists in `marketreadiness.db`. The API seeds the committed snapshot only when the store has no active dataset.

## Windows (PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
```

In a second PowerShell window:

```powershell
npm install --global pnpm@11.25.0
cd apps/web
pnpm install --frozen-lockfile
pnpm dev
```

Commands avoid requiring PowerShell activation-policy changes. To enable local AI, set environment variables explicitly, for example `$env:LLM_PROVIDER='ollama'`. Native execution does not automatically load `.env`; Compose does.

## Checks

From the project root with the environment active:

```bash
ruff check packages apps/api tests scripts
ruff format --check packages apps/api tests scripts
pytest
python -m marketreadiness.evaluation.benchmark
python scripts/licenses.py
```

From `apps/web`:

```bash
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm exec playwright install chromium
pnpm test:e2e
```

For a running Compose stack: `E2E_BASE_URL=http://localhost:8080 pnpm test:e2e`. On Windows use `$env:E2E_BASE_URL='http://localhost:8080'` before the test command. CI installs the open-source Playwright Chromium build; an existing Chrome executable can be used locally via `PLAYWRIGHT_CHROME_PATH`.

The e2e suite writes screenshots into `docs/images`. It also saves a scenario and deliberately submits a rejected dataset. Use a disposable demo database for repeated browser QA. Its baseline remains unchanged.

## PostgreSQL validation

Use a disposable database and set `TEST_DATABASE_URL=postgresql+psycopg://user:password@localhost/test_database` before running pytest. The API initializes its tables. In Compose, the initialization SQL creates an unprivileged writer plus a SELECT-only reader. CI covers both a PostgreSQL test database and the complete Compose application. Credentials in the examples are public demo/CI values, not production secrets.

## Troubleshooting

- **Ports already in use:** stop your previous instance or change both the API listener and Vite proxy together. Default supported demo origins are localhost/127.0.0.1 on 5173, 8080 or 8000.
- **Container remains unready:** inspect `docker compose logs api db`. PostgreSQL role initialization runs only on a new volume. Preserve any data you need before resetting a demo volume.
- **Model unavailable:** verify `ollama list`, the exact `LLM_MODEL` name, and `OLLAMA_BASE_URL`. Briefs fall back; readiness is independent of the model.
- **Ollama on native macOS:** container inference does not use native Metal by default. For native API use `http://localhost:11434`; for a container reaching native Ollama use `http://host.docker.internal:11434` and configure the runtime listener appropriately.
- **Readiness did not change after import:** inspect the validation report; rejected imports never replace the active snapshot. A changed dataset must have a new dataset ID.
- **Idempotency conflict:** repeat the identical body with the original key, or use a new key for a new operation.
- **No transfer recommendations:** the deadline, donor score, regional constraint or minimum projected donor balance may prohibit the move. A null completion is honest when supply evidence is insufficient.

## Updating dependencies

Python versions are locked in `requirements.txt` / `requirements-dev.txt`; frontend versions are locked in `pnpm-lock.yaml`. Update deliberately, run tests and audits, then regenerate license inventory and benchmarks if behavior changes. `scripts/lock_python.py` captures installed Python versions without local editable paths. OS and container-image licenses are not covered by Python/pnpm metadata alone.
