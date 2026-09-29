"""Application orchestration. HTTP handlers only validate/dispatch requests."""

import csv
import io
from pathlib import Path

from marketreadiness.ai.briefing import create_brief
from marketreadiness.data.store import Store, fingerprint
from marketreadiness.data.validation import TABLES, validate_dataset
from marketreadiness.domain.forecast import forecast
from marketreadiness.domain.planning import plan
from marketreadiness.domain.schemas import Dataset, Guardrails, PlanningResult, Scenario
from marketreadiness.domain.transfers import recommend


class PortfolioService:
    def __init__(self, store: Store, runtime=None):
        self.store, self.runtime = store, runtime

    def seed(self, path: Path):
        if self.store.active() is None:
            import json

            self.ingest(json.loads(path.read_text()), "bootstrap-demo-v1")

    def dataset(self) -> Dataset:
        data = self.store.active()
        if not data:
            raise LookupError("No active dataset")
        return data

    def ingest(self, raw: dict, key: str):
        data, report = validate_dataset(raw)
        digest = fingerprint(raw)
        docs = [(report.id, "validation", report.model_dump(mode="json"))]
        response = report.model_dump(mode="json")
        if data:
            docs.append((data.id, "dataset", data.model_dump(mode="json")))
        return self.store.write(f"import:{key}", digest, docs, response, data.id if data else None)

    def baseline(self):
        return plan(self.dataset())

    def result(self, run_id: str | None):
        if not run_id:
            return self.baseline()
        raw = self.store.get(run_id)
        if not raw or "algorithm_version" not in raw:
            raise LookupError("Planning result not found")
        return PlanningResult.model_validate(raw)

    def scenario(self, scenario: Scenario, key: str):
        data = self.dataset()
        result = plan(data, scenario)
        payload = result.model_dump(mode="json")
        return self.store.write(
            f"scenario:{key}",
            fingerprint({"scenario": scenario.model_dump(mode="json"), "dataset_id": data.id}),
            [(result.id, "scenario", payload)],
            payload,
        )

    def compare(self, left: str | None, right: str):
        baseline, scenario = self.result(left), self.result(right)
        if baseline.dataset_id != scenario.dataset_id:
            raise ValueError("Scenarios from different datasets cannot be compared")
        old = {m.market_id: m for m in baseline.markets}
        return {
            "baseline_id": baseline.id,
            "scenario_id": scenario.id,
            "readiness_delta": round(scenario.readiness - baseline.readiness, 2),
            "markets": [
                {
                    "market_id": m.market_id,
                    "name": m.name,
                    "baseline": old[m.market_id].readiness,
                    "scenario": m.readiness,
                    "delta": round(m.readiness - old[m.market_id].readiness, 2),
                    "baseline_constraint": old[m.market_id].earliest_constraint,
                    "scenario_constraint": m.earliest_constraint,
                }
                for m in scenario.markets
            ],
        }

    def transfers(self, run_id: str | None, guardrails: Guardrails):
        result = self.result(run_id)
        raw = self.store.get(result.dataset_id)
        return recommend(Dataset.model_validate(raw), result, guardrails)

    def forecasts(self):
        return forecast(self.dataset())

    def brief(self, run_id, period, trace_id=None):
        return create_brief(self.result(run_id), period, self.runtime, trace_id=trace_id)

    def records(self, table: str, offset: int, limit: int):
        if table not in TABLES:
            raise LookupError("Unknown dataset table")
        rows = getattr(self.dataset(), table)
        return {
            "items": [r.model_dump(mode="json") for r in rows[offset : offset + limit]],
            "total": len(rows),
            "offset": offset,
            "limit": limit,
        }

    def csv(self):
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            ["market", "region", "readiness_percent", "status", "earliest_constraint", "blockers"]
        )
        for m in self.baseline().markets:
            # Neutralize spreadsheet formulas in imported market names.
            def safe(s):
                return "'" + s if s.startswith(("=", "+", "-", "@", "\t", "\r")) else s

            writer.writerow(
                [
                    safe(m.name),
                    safe(m.region),
                    m.readiness,
                    m.status,
                    m.earliest_constraint,
                    m.blockers,
                ]
            )
        return output.getvalue()
