import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app


@pytest.fixture
def client(tmp_path):
    # CI can exercise the identical suite against a real PostgreSQL service.
    database_url = os.getenv("TEST_DATABASE_URL") or f"sqlite:///{tmp_path / 'test.db'}"
    app = create_app(database_url=database_url, mode="demo")
    with TestClient(app) as c:
        yield c


def test_primary_workflow(client):
    assert client.get("/health/ready").status_code == 200
    p = client.get("/api/v1/portfolio")
    assert p.status_code == 200 and p.headers["x-trace-id"]
    baseline = p.json()
    assert len(baseline["markets"]) == 14
    key = {"Idempotency-Key": "test-workflow-001"}
    body = {"name": "Delay", "po_delays": {"po-m00-00-fiber": 10}, "accelerate_days": 7}
    scenario = client.post("/api/v1/scenarios", json=body, headers=key)
    assert scenario.status_code == 201
    assert client.post("/api/v1/scenarios", json=body, headers=key).json() == scenario.json()
    assert client.get("/api/v1/portfolio").json() == baseline
    comparison = client.get("/api/v1/compare", params={"right": scenario.json()["id"]})
    assert comparison.status_code == 200
    assert comparison.json()["readiness_delta"] <= 0
    assert client.post("/api/v1/transfers", json={}).json()
    brief = client.post("/api/v1/briefs", json={}).json()
    assert brief["mode"] == "deterministic" and brief["statements"][0]["source_ids"]
    assert client.get("/api/v1/forecast").json()["status"] == "ok"
    assert client.get("/api/v1/exports/readiness.csv").text.startswith("market,region")


def test_invalid_import_atomic_and_reported(client):
    baseline = client.get("/api/v1/portfolio").json()
    raw = {"id": "invalid-dataset", "markets": [{"id": "bad"}]}
    response = client.post(
        "/api/v1/imports", json=raw, headers={"Idempotency-Key": "invalid-import-001"}
    )
    assert response.status_code == 200
    assert not response.json()["accepted"] and response.json()["issues"]
    assert client.get("/api/v1/portfolio").json() == baseline
    assert any(not r["accepted"] for r in client.get("/api/v1/validation-reports").json())


def test_idempotency_conflict(client):
    headers = {"Idempotency-Key": "conflict-key-001"}
    assert (
        client.post("/api/v1/scenarios", json={"name": "first"}, headers=headers).status_code == 201
    )
    assert (
        client.post("/api/v1/scenarios", json={"name": "second"}, headers=headers).status_code
        == 409
    )


@pytest.mark.parametrize(
    "path,status",
    [
        ("/api/v1/records/nope", 404),
        ("/api/v1/markets/nope", 404),
        ("/api/v1/records/inventory?limit=501", 422),
        ("/api/v1/records/inventory?offset=-1", 422),
        ("/api/v1/scenarios/not-found", 404),
    ],
)
def test_error_envelopes(client, path, status):
    response = client.get(path)
    assert response.status_code == status
    assert response.json()["error"]["trace_id"]


def test_malformed_mime_size_and_origin(client):
    headers = {"Idempotency-Key": "malformed-001"}
    assert client.post("/api/v1/imports", content="hi", headers=headers).status_code == 415
    assert (
        client.post(
            "/api/v1/imports", content="{", headers={**headers, "Content-Type": "application/json"}
        ).status_code
        == 400
    )
    assert client.post("/api/v1/imports", json=[], headers=headers).status_code == 422
    assert (
        client.post(
            "/api/v1/scenarios", json={}, headers={**headers, "Origin": "https://attacker.example"}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/imports",
            content="x" * (20 * 1024 * 1024 + 1),
            headers={**headers, "Content-Type": "application/json"},
        ).status_code
        == 413
    )


def test_read_and_write_authorization(tmp_path, monkeypatch):
    monkeypatch.setenv("READ_API_TOKEN", "r" * 32)
    monkeypatch.setenv("WRITE_API_TOKEN", "w" * 32)
    with TestClient(
        create_app(database_url=f"sqlite:///{tmp_path / 'secured.db'}", mode="secured")
    ) as c:
        assert c.get("/api/v1/portfolio").status_code == 401
        read = {"Authorization": "Bearer " + "r" * 32}
        assert c.get("/api/v1/portfolio", headers=read).status_code == 200
        assert (
            c.post(
                "/api/v1/scenarios", json={}, headers={**read, "Idempotency-Key": "auth-read-001"}
            ).status_code
            == 401
        )
        assert (
            c.post(
                "/api/v1/scenarios",
                json={},
                headers={
                    "Authorization": "Bearer " + "w" * 32,
                    "Idempotency-Key": "auth-write-001",
                },
            ).status_code
            == 201
        )
        assert c.get("/docs").status_code == 404


def test_database_survives_restart(tmp_path):
    url = f"sqlite:///{tmp_path / 'persist.db'}"
    with TestClient(create_app(database_url=url)) as c:
        result = c.post(
            "/api/v1/scenarios",
            json={"name": "Saved"},
            headers={"Idempotency-Key": "persist-key-001"},
        ).json()
    with TestClient(create_app(database_url=url)) as c:
        assert c.get("/api/v1/scenarios/" + result["id"]).json() == result


def test_schema_and_committed_sample_in_sync():
    import json

    from marketreadiness.data.generator import generate
    from marketreadiness.domain.schemas import Dataset

    assert (
        json.loads(Path("data/schemas/dataset.schema.json").read_text())
        == Dataset.model_json_schema()
    )
    assert json.loads(Path("data/sample/portfolio.json").read_text()) == generate().model_dump(
        mode="json"
    )


def test_invalid_host_has_safe_envelope(client):
    response = client.get("/api/v1/portfolio", headers={"Host": "attacker.example"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_host"


def test_brief_correlates_trace_and_episode(client):
    response = client.post("/api/v1/briefs", json={})
    assert response.json()["telemetry"]["request_trace_id"] == response.headers["X-Trace-ID"]


def test_valid_import_activates_new_immutable_snapshot(tmp_path):
    import json

    raw = json.loads(Path("data/sample/portfolio.json").read_text())
    raw["id"] = "accepted-import-test-v2"
    with TestClient(create_app(database_url=f"sqlite:///{tmp_path / 'import.db'}")) as c:
        response = c.post(
            "/api/v1/imports", json=raw, headers={"Idempotency-Key": "valid-import-001"}
        )
        assert response.json()["accepted"]
        assert c.get("/api/v1/portfolio").json()["dataset_id"] == raw["id"]
        raw["markets"][0]["name"] = "Attempted in-place mutation"
        assert (
            c.post(
                "/api/v1/imports", json=raw, headers={"Idempotency-Key": "valid-import-002"}
            ).status_code
            == 409
        )
        assert c.get("/api/v1/portfolio").json()["markets"][0]["name"] == "Austin"


def test_openapi_explorer_uses_local_assets(client):
    html = client.get("/docs").text
    assert "/docs-assets/swagger-ui-bundle.js" in html
    assert "cdn.jsdelivr.net" not in html
    assert '"validatorUrl": null' in html
    assert client.get("/docs-assets/swagger-ui.css").status_code == 200


def test_import_contract_is_in_openapi(client):
    spec = client.get("/openapi.json").json()
    assert (
        spec["paths"]["/api/v1/imports"]["post"]["requestBody"]["content"]["application/json"][
            "schema"
        ]["$ref"]
        == "#/components/schemas/Dataset"
    )
    assert "Inventory" in spec["components"]["schemas"]
