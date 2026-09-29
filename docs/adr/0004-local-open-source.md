# ADR 0004: Locally runnable open-source defaults

Status: accepted.

The distribution uses Python, FastAPI, Polars, SQLAlchemy, PostgreSQL, React, Vite, ECharts, Nginx and optional Ollama. No external credentials, paid API, proprietary cloud AI or hosted connector are on the core path. Local model weights are downloaded separately under their own terms. A protocol isolates local runtime implementation from business logic.

The requested repository is a portable monorepo, not a hosted Sites app. UI design guidance is applied locally; deployment to a proprietary hosting service is not part of this deliverable. Docker Compose targets an open-source Docker Engine or a compatible local engine. Docker Desktop is not a required dependency.

Consequence: simple offline operation after initial package/image/model downloads; hardware setup and upgrades remain the operator's responsibility. Native SQLite and container PostgreSQL both require explicit validation; success in one is not evidence that the other ran.
