"""Render exact approved facts; the language model only chooses their order."""

import logging
import time
from uuid import uuid4

from marketreadiness.ai.runtime import PROMPT_VERSION, LocalRuntime
from marketreadiness.domain.schemas import Brief, Evidence, PlanningResult

logger = logging.getLogger("marketreadiness")


def evidence_for(result: PlanningResult) -> list[Evidence]:
    if not result.requirements:
        return []
    evidence = [
        Evidence(
            id=f"{result.id}:portfolio",
            text=f"Portfolio readiness is {result.readiness:.1f}% across {len(result.markets)} markets.",
            source_ids=[result.id],
        )
    ]
    for m in sorted(
        result.markets,
        key=lambda m: (
            m.earliest_constraint is None,
            m.earliest_constraint or result.as_of,
            m.readiness,
        ),
    ):
        blockers = [r for r in result.requirements if r.market_id == m.market_id and r.shortage]
        if blockers:
            text = f"{m.name}: {m.readiness:.1f}% readiness; {m.blockers} material blockers; first constraint {m.earliest_constraint}."
            evidence.append(
                Evidence(
                    id=f"{result.id}:{m.market_id}",
                    text=text,
                    source_ids=[m.market_id, *[r.id for r in blockers]],
                )
            )
    for req in sorted(
        (r for r in result.requirements if r.shortage), key=lambda r: (r.due_date, r.id)
    )[:12]:
        evidence.append(
            Evidence(
                id=req.id,
                text=f"{req.market_id} needs {req.shortage:,} additional {req.material_id} units by {req.due_date}; confirmed material availability: {req.material_ready_date or 'unresolved within horizon'}.",
                source_ids=req.source_ids,
            )
        )
    return evidence


def create_brief(
    result: PlanningResult,
    period="weekly",
    runtime: LocalRuntime | None = None,
    trace_id: str | None = None,
) -> Brief:
    evidence = evidence_for(result)
    telemetry = {
        "episode_id": str(uuid4()),
        "request_trace_id": trace_id,
        "data_version": result.dataset_id,
        "result_id": result.id,
        "algorithm_version": result.algorithm_version,
        "prompt_version": PROMPT_VERSION,
        "provider": runtime.provider if runtime else "none",
        "model": runtime.model if runtime else None,
        "retries": 0,
        "validation_failures": 0,
        "runtime_failures": 0,
        "tool_calls": [],
        "input_source_ids": [e.id for e in evidence],
        "seed": 42,
    }
    start = time.perf_counter()
    statement_limit = 4 if period == "daily" else 8
    chosen = evidence[:statement_limit]
    mode = "deterministic" if evidence else "abstained"
    if runtime and evidence:
        for attempt in range(2):
            try:
                selection, metadata = runtime.select(evidence)
                lookup = {e.id: e for e in evidence}
                if (
                    len(selection.evidence_ids) != len(set(selection.evidence_ids))
                    or set(selection.evidence_ids) - lookup.keys()
                ):
                    raise ValueError("Unknown or duplicate evidence IDs")
                has_risk = any(m.status != "Ready" for m in result.markets)
                if selection.posture != "abstain" and (
                    not selection.evidence_ids
                    or selection.posture != ("attention" if has_risk else "ready")
                ):
                    raise ValueError("Posture contradicts deterministic evidence")
                if selection.posture == "abstain" and selection.evidence_ids:
                    raise ValueError("Abstention must contain no claims")
                chosen = [lookup[id] for id in selection.evidence_ids[:statement_limit]]
                mode = "abstained" if selection.posture == "abstain" else "local-llm"
                telemetry.update(metadata)
                break
            except Exception as exc:
                # Fail closed to verified facts. Never modify a plan or store model text.
                telemetry[
                    "validation_failures" if isinstance(exc, ValueError) else "runtime_failures"
                ] += 1
                telemetry["retries"] = attempt
                telemetry["last_error_type"] = type(exc).__name__
                mode = "fallback"
    telemetry["latency_ms"] = round((time.perf_counter() - start) * 1000, 2)
    logger.info("brief_complete", extra={"event_data": telemetry})
    headline = (
        "Evidence unavailable — briefing abstained"
        if mode == "abstained"
        else (
            "Material constraints need attention"
            if any(m.status != "Ready" for m in result.markets)
            else "All planned markets are material-ready"
        )
    )
    return Brief(
        id=f"brief-{uuid4()}",
        period=period,
        mode=mode,
        headline=headline,
        statements=chosen if mode != "abstained" else [],
        telemetry=telemetry,
    )
