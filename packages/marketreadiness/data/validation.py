"""Validate atomically. Invalid rows stay visible in a report; no partial imports."""

import json
from collections import Counter
from hashlib import sha256

from pydantic import ValidationError

from marketreadiness.domain.schemas import Dataset, ValidationIssue, ValidationReport

TABLES = (
    "markets",
    "materials",
    "boms",
    "plans",
    "inventory",
    "purchase_orders",
    "commitments",
    "consumption",
)


def validate_dataset(raw: dict) -> tuple[Dataset | None, ValidationReport]:
    issues = []
    count = sum(len(raw.get(t, [])) for t in TABLES if isinstance(raw.get(t), list))
    digest = sha256(json.dumps(raw, sort_keys=True, default=str).encode()).hexdigest()[:20]
    report = ValidationReport(
        id=f"validation-{digest}",
        accepted=False,
        dataset_id=str(raw.get("id", "unknown"))[:100],
        checked_records=count,
        issues=[],
    )
    try:
        data = Dataset.model_validate(raw)
    except ValidationError as exc:
        for e in exc.errors(include_input=False, include_url=False):
            loc = e["loc"]
            table = str(loc[0]) if loc else "dataset"
            idx = loc[1] if len(loc) > 1 and isinstance(loc[1], int) else None
            rows = raw.get(table, [])
            row = (
                rows[idx] if idx is not None and isinstance(rows, list) and idx < len(rows) else {}
            )
            issues.append(
                ValidationIssue(
                    table=table,
                    record_id=str(row.get("id", idx)) if isinstance(row, dict) else None,
                    field=".".join(map(str, loc)),
                    severity="error",
                    message=e["msg"],
                )
            )
        report.issues = issues
        return None, report

    def issue(table, row, msg, severity="error"):
        issues.append(
            ValidationIssue(table=table, record_id=row.id, severity=severity, message=msg)
        )

    all_ids = [r.id for t in TABLES for r in getattr(data, t)]
    duplicates = {k for k, v in Counter(all_ids).items() if v > 1}
    markets = {r.id for r in data.markets}
    materials = {r.id for r in data.materials}
    plans = {r.id: r for r in data.plans}
    orders = {r.id for r in data.purchase_orders}
    bom_phases = {r.phase for r in data.boms}
    for table in TABLES:
        for row in getattr(data, table):
            if row.id in duplicates:
                issue(table, row, "Duplicate record ID across dataset")
            if hasattr(row, "market_id") and row.market_id not in markets:
                issue(table, row, "Unknown market_id")
            if hasattr(row, "material_id") and row.material_id not in materials:
                issue(table, row, "Unknown material_id")
    cohort_sizes = {}
    phase_keys = set()
    for p in data.plans:
        key = (p.market_id, p.phase)
        if key in phase_keys:
            issue("plans", p, "Only one build cohort per market and phase is supported")
        phase_keys.add(key)
        if p.market_id in cohort_sizes and cohort_sizes[p.market_id] != p.homes:
            issue("plans", p, "All phases in one market must describe the same home cohort")
        cohort_sizes[p.market_id] = p.homes
        if p.start < data.as_of:
            issue("plans", p, "Plan starts before as_of; completed work belongs in consumption")
        if p.phase not in bom_phases:
            issue("plans", p, "Missing BOM for phase")
        seen = {p.id}
        parent = p.predecessor_id
        while parent:
            if parent not in plans:
                issue("plans", p, "Unknown predecessor")
                break
            if parent in seen:
                issue("plans", p, "Cyclic phase dependency")
                break
            seen.add(parent)
            prior = plans[parent]
            if prior.market_id != p.market_id:
                issue("plans", p, "Cross-market dependency is not supported")
                break
            parent = prior.predecessor_id
    for r in data.inventory:
        if r.snapshot_date != data.as_of:
            issue("inventory", r, "Inventory snapshot must match as_of")
        if r.quarantined:
            issue("inventory", r, "Quarantined stock excluded from available supply", "warning")
    for r in data.commitments:
        if r.po_id not in orders:
            issue("commitments", r, "Unknown po_id")
        if r.updated_at.tzinfo is None or r.updated_at.date() > data.as_of:
            issue(
                "commitments", r, "Commitment must be timezone-aware and known as of planning date"
            )
    for r in data.purchase_orders:
        if r.expected_date < data.as_of and r.status == "open":
            issue(
                "purchase_orders",
                r,
                "Overdue receipt: excluded unless a confirmed future commitment exists",
                "warning",
            )
    for r in data.consumption:
        if r.date >= data.as_of:
            issue("consumption", r, "History must precede as_of to avoid forecast leakage")
    report.issues = issues
    report.accepted = not any(i.severity == "error" for i in issues)
    return (data if report.accepted else None), report
