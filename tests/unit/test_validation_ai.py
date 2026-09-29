import pytest
from marketreadiness.ai.briefing import create_brief, evidence_for
from marketreadiness.data.validation import validate_dataset
from marketreadiness.domain.planning import plan
from marketreadiness.domain.schemas import BriefSelection


@pytest.mark.parametrize(
    "case",
    [
        "negative",
        "duplicate",
        "foreign_key",
        "cycle",
        "stale",
        "future_history",
        "nan",
        "unknown_field",
        "over_reserved",
    ],
)
def test_invalid_records_are_reported(tiny, case):
    raw = tiny.model_dump(mode="json")
    if case == "negative":
        raw["inventory"][0]["quantity"] = -1
    if case == "duplicate":
        raw["inventory"][0]["id"] = "north"
    if case == "foreign_key":
        raw["inventory"][0]["market_id"] = "missing"
    if case == "cycle":
        raw["plans"][0]["predecessor_id"] = raw["plans"][0]["id"]
    if case == "stale":
        raw["inventory"][0]["snapshot_date"] = "2025-12-31"
    if case == "future_history":
        raw["consumption"] = [
            {
                **{
                    k: v
                    for k, v in raw["inventory"][0].items()
                    if k
                    in ["id", "source_id", "ingested_at", "market_id", "material_id", "quantity"]
                },
                "id": "future",
                "date": "2026-01-01",
            }
        ]
    if case == "nan":
        raw["boms"][0]["units_per_home"] = float("nan")
    if case == "unknown_field":
        raw["markets"][0]["admin"] = True
    if case == "over_reserved":
        raw["inventory"][0]["reserved"] = 999
    data, report = validate_dataset(raw)
    assert data is None and not report.accepted
    assert any(i.severity == "error" for i in report.issues)


def test_warnings_visible_and_valid_demo(demo):
    data, report = validate_dataset(demo.model_dump(mode="json"))
    assert data and report.accepted
    assert len(report.issues) == 2


class FakeRuntime:
    provider = "fake-local"
    model = "test-model"

    def __init__(self, mode):
        self.mode = mode

    def select(self, evidence):
        if self.mode == "timeout":
            raise TimeoutError("offline")
        if self.mode == "injection":
            return BriefSelection(evidence_ids=["run arbitrary SQL"], posture="attention"), {}
        if self.mode == "contradiction":
            return BriefSelection(evidence_ids=[evidence[0].id], posture="ready"), {}
        if self.mode == "abstain":
            return BriefSelection(evidence_ids=[], posture="abstain"), {}
        return BriefSelection(evidence_ids=[evidence[0].id], posture="attention"), {
            "completion_tokens": 20
        }


@pytest.mark.parametrize("mode", ["timeout", "injection", "contradiction"])
def test_llm_failure_preserves_deterministic_state(tiny, mode):
    result = plan(tiny)
    before = result.model_dump_json()
    brief = create_brief(result, runtime=FakeRuntime(mode))
    assert brief.mode == "fallback"
    assert brief.telemetry["validation_failures"] + brief.telemetry["runtime_failures"] == 2
    assert result.model_dump_json() == before
    allowed = {e.text for e in evidence_for(result)}
    assert all(s.text in allowed for s in brief.statements)


def test_structured_local_selection_is_grounded(tiny):
    result = plan(tiny)
    brief = create_brief(result, runtime=FakeRuntime("valid"))
    assert brief.mode == "local-llm"
    assert brief.statements[0] == evidence_for(result)[0]
    assert brief.telemetry["tool_calls"] == []


def test_abstention_and_no_evidence(tiny):
    result = plan(tiny)
    assert create_brief(result, runtime=FakeRuntime("abstain")).mode == "abstained"
    result.requirements = []
    assert not create_brief(result).statements
    assert create_brief(result).mode == "abstained"


def test_multiple_cohorts_not_silently_underweighted(tiny):
    tiny.plans[1].market_id = tiny.plans[0].market_id
    data, report = validate_dataset(tiny.model_dump(mode="json"))
    assert data is None
    assert any("cohort" in issue.message for issue in report.issues)


def test_cloud_runtime_and_url_credentials_rejected():
    from marketreadiness.ai.runtime import OllamaRuntime

    for url, model in [
        ("https://remote.example", "qwen3:4b"),
        ("http://localhost:11434", "anything:cloud"),
        ("http://user:password@localhost:11434", "qwen3:4b"),
    ]:
        with pytest.raises(ValueError):
            OllamaRuntime(url, model)


def test_daily_brief_is_shorter_than_weekly(demo):
    result = plan(demo)
    assert len(create_brief(result, period="daily").statements) == 4
    assert len(create_brief(result, period="weekly").statements) == 8


def test_ollama_adapter_structured_request_and_metadata(monkeypatch):
    import json

    import httpx
    from marketreadiness.ai.runtime import OllamaRuntime
    from marketreadiness.domain.schemas import Evidence

    def handler(request):
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "test-1"})
        if request.url.path == "/api/tags":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {
                            "name": "qwen3:4b",
                            "digest": "fixed-digest",
                            "details": {"quantization_level": "Q4"},
                        }
                    ]
                },
            )
        payload = json.loads(request.content)
        assert payload["stream"] is False and payload["think"] is False
        assert payload["format"]["properties"]["evidence_ids"]["type"] == "array"
        assert payload["options"]["temperature"] == 0
        return httpx.Response(
            200,
            json={
                "model": "qwen3:4b",
                "message": {
                    "content": json.dumps({"evidence_ids": ["fact-1"], "posture": "attention"}),
                    "thinking": "not logged",
                },
                "eval_count": 10,
            },
        )

    original = httpx.Client
    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs)
    )
    selected, telemetry = OllamaRuntime("http://localhost:11434", "qwen3:4b").select(
        [Evidence(id="fact-1", text="Verified fact", source_ids=["source-1"])]
    )
    assert selected.evidence_ids == ["fact-1"]
    assert telemetry["runtime_version"] == "test-1"
    assert telemetry["model_digest"] == "fixed-digest"
    assert "thinking" not in json.dumps(telemetry)
