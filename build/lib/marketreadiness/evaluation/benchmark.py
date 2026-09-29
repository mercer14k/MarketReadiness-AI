"""Reproducible correctness + timing harness. No network unless --model is supplied."""

import argparse
import csv
import importlib.metadata
import json
import os
import platform
import statistics
import subprocess
import time
import tracemalloc
from datetime import UTC, datetime
from pathlib import Path

from marketreadiness.ai.briefing import create_brief, evidence_for
from marketreadiness.ai.runtime import OllamaRuntime
from marketreadiness.data.generator import generate
from marketreadiness.data.validation import TABLES, validate_dataset
from marketreadiness.domain.forecast import forecast
from marketreadiness.domain.planning import plan
from marketreadiness.domain.transfers import recommend


def hardware():
    cpu = platform.processor() or platform.machine()
    memory = None
    if platform.system() == "Darwin":
        try:
            cpu = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"], text=True
            ).strip()
            memory = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True))
        except (OSError, subprocess.CalledProcessError):
            pass
    return {
        "os": platform.platform(),
        "architecture": platform.machine(),
        "cpu": cpu,
        "logical_cpus": os.cpu_count(),
        "ram_bytes": memory,
        "python": platform.python_version(),
        "versions": {
            name: importlib.metadata.version(name)
            for name in ["fastapi", "polars", "pydantic", "sqlalchemy"]
        },
    }


def run(output: Path, scale: int, repeats: int, model: str | None, url: str):
    data = generate()
    validated, report = validate_dataset(data.model_dump(mode="json"))
    assert validated and report.accepted
    result = plan(data)
    truth_path = Path("data/sample/ground-truth.json")
    truth = json.loads(truth_path.read_text())
    actual = {
        m.market_id: m.earliest_constraint.isoformat() if m.earliest_constraint else None
        for m in result.markets
    }
    exact = sum(actual[k] == v for k, v in truth["constraints"].items())
    date_errors = [
        abs((datetime.fromisoformat(actual[k]) - datetime.fromisoformat(v)).days)
        for k, v in truth["constraints"].items()
        if v and actual[k]
    ]
    transfers = recommend(data, result)
    valid = sum(
        t.arrival_date <= t.need_date and t.donor_min_balance_after >= t.safety_stock
        for t in transfers
    )
    predictions = forecast(data)
    runtime = OllamaRuntime(url, model, timeout=60) if model else None
    brief = create_brief(result, runtime=runtime)
    reference = {e.id: e for e in evidence_for(result)}
    grounded = sum(s.id in reference and s == reference[s.id] for s in brief.statements)
    evaluation = {
        "constraint_exact_matches": exact,
        "constraint_cases": len(actual),
        "constraint_date_mae_days_matched_cases": statistics.mean(date_errors),
        "constraint_date_cases_matched": len(date_errors),
        "readiness_actual": result.readiness,
        "readiness_expected": truth["expected_portfolio_readiness"],
        "readiness_absolute_error": abs(result.readiness - truth["expected_portfolio_readiness"]),
        "forecast_wape": predictions["wape"],
        "forecast_backtest_observations": predictions["backtest_observations"],
        "transfer_rule_passes": valid,
        "transfer_cases": len(transfers),
        "grounded_statements": grounded,
        "statement_count": len(brief.statements),
        "brief_mode": brief.mode,
    }
    timings = []
    for multiplier in sorted({1, scale}):
        dataset = generate(scale=multiplier)
        plan(dataset)  # one untimed warm-up
        elapsed = []
        for _ in range(repeats):
            start = time.perf_counter()
            run_result = plan(dataset)
            elapsed.append((time.perf_counter() - start) * 1000)
        tracemalloc.start()
        plan(dataset)  # separate memory pass; excluded from timing
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        timings.append(
            {
                "markets": len(dataset.markets),
                "records": sum(len(getattr(dataset, t)) for t in TABLES),
                "requirements": len(run_result.requirements),
                "seed": dataset.seed,
                "median_ms": round(statistics.median(elapsed), 3),
                "max_ms": round(max(elapsed), 3),
                "min_ms": round(min(elapsed), 3),
                "repeats": repeats,
                "python_peak_allocated_mib": round(peak / 1024 / 1024, 3),
                "samples_ms": elapsed,
            }
        )
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "hardware": hardware(),
        "configuration": {
            "seed": 42,
            "algorithm": "mrp-1.0",
            "horizon_days": 90,
            "forecast": "weekday-mean-v1",
            "llm_model": model,
            "memory_method": "tracemalloc separate untimed pass; excludes native Polars allocations and model memory",
        },
        "evaluation": evaluation,
        "performance": timings,
        "llm_telemetry": brief.telemetry,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    with (output / "performance.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[k for k in timings[0] if k != "samples_ms"])
        writer.writeheader()
        writer.writerows({k: v for k, v in row.items() if k != "samples_ms"} for row in timings)
    with (output / "evaluation.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        writer.writerows(evaluation.items())
    rows = "\n".join(
        f"| {r['markets']} | {r['records']:,} | {r['median_ms']:.1f} | {r['max_ms']:.1f} | {r['python_peak_allocated_mib']:.1f} |"
        for r in timings
    )
    md = f"""# Measured benchmark example

Generated: {report["generated_at"]}. Hardware: **{report["hardware"]["cpu"]}**, {report["hardware"]["os"]}, Python {report["hardware"]["python"]}.

Configuration: seed 42; 90-day horizon; mrp-1.0; {repeats} warm runs. LLM: {model or "disabled"}; actual briefing mode: **{brief.mode}**.

| Markets | Source records | Median (ms) | Maximum (ms) | Python peak allocated (MiB) |
|---:|---:|---:|---:|---:|
{rows}

Timing covers planning and result hashing; excludes file parsing, database, forecast, HTTP, UI and LLM. Memory is a separate tracemalloc pass and excludes native allocations. Maximum is not a p95 claim.

| Evaluation | Measured result |
|---|---|
| Constraint dates / no-constraint classifications | {exact}/{len(actual)} exact synthetic fixture matches |
| Constraint date MAE | {evaluation["constraint_date_mae_days_matched_cases"]:.1f} days on {len(date_errors)} matched constrained markets |
| Portfolio readiness absolute error | {evaluation["readiness_absolute_error"]:.2f} percentage points |
| Consumption forecast WAPE | {predictions["wape"]:.2%} on {predictions["backtest_observations"]} held-out observations |
| Transfer timing / safety-floor checks | {valid}/{len(transfers)} recommendations pass |
| Explanation evidence equality | {grounded}/{len(brief.statements)} statements grounded |

These are synthetic regression and diagnostic results, **not real-world accuracy claims**. Grounding is guaranteed by exact evidence rendering, not a measure of model judgment. An abstaining model produces zero claims; zero claims are never reported as 100% success. See results.json for actual runtime/configuration, validation failures, tokens and latency. Forecast WAPE pools units and is dominated by high-volume fiber/conduit; use per-material API metrics when assessing individual series.
"""
    (output / "summary.md").write_text(md)
    print(json.dumps(report, indent=2))
    assert exact == len(actual) and valid == len(transfers) and grounded == len(brief.statements)
    assert evaluation["readiness_absolute_error"] == 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("artifacts/benchmark"))
    parser.add_argument("--scale", type=int, default=10)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--model", default=None)
    parser.add_argument("--ollama-url", default="http://localhost:11434")
    args = parser.parse_args()
    if not 1 <= args.repeats <= 100:
        parser.error("repeats must be 1..100")
    run(args.output, args.scale, args.repeats, args.model, args.ollama_url)


if __name__ == "__main__":
    main()
