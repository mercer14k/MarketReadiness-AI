"""Time-phased, finite-supply planning. No model calls or database dependencies."""

from collections import defaultdict
from datetime import timedelta
from decimal import ROUND_CEILING, Decimal
from hashlib import sha256

from marketreadiness.domain.schemas import (
    Dataset,
    LedgerPoint,
    MarketResult,
    PhaseResult,
    PlanningResult,
    Requirement,
    Scenario,
    TimelinePoint,
)

ALGORITHM_VERSION = "mrp-1.0"


def quantity(homes: int, rate: float) -> int:
    return int((Decimal(homes) * Decimal(str(rate))).to_integral_value(rounding=ROUND_CEILING))


def plan(data: Dataset, scenario: Scenario | None = None) -> PlanningResult:
    scenario = scenario or Scenario()
    order_ids = {x.id for x in data.purchase_orders}
    market_ids = {x.id for x in data.markets}
    if set(scenario.po_delays) - order_ids or set(scenario.market_ids) - market_ids:
        raise ValueError("Scenario references an unknown PO or market")
    horizon = data.as_of + timedelta(days=scenario.horizon_days)
    materials = {x.id: x for x in data.materials}
    markets = {x.id: x for x in data.markets}
    selected = set(scenario.market_ids) or market_ids
    planned_dates = {
        p.id: max(
            data.as_of,
            p.start - timedelta(days=scenario.accelerate_days if p.market_id in selected else 0),
        )
        for p in data.plans
    }
    plans = [p for p in data.plans if planned_dates[p.id] <= horizon]
    plans.sort(key=lambda p: (planned_dates[p.id], -markets[p.market_id].priority, p.id))
    supplies = defaultdict(list)
    source_ids = defaultdict(list)
    events = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    warnings = []
    snapshots = set()
    for inv in data.inventory:
        key = (inv.market_id, inv.material_id)
        snapshots.add(key)
        usable = inv.quantity - inv.reserved - inv.quarantined
        supplies[key].append([data.as_of, usable, inv.id])
        source_ids[key].append(inv.id)
        events[key][data.as_of][0] += usable
    latest = {}
    for c in sorted(data.commitments, key=lambda x: (x.updated_at, x.id)):
        latest[c.po_id] = c
    for po in data.purchase_orders:
        if po.status != "open" or po.received == po.quantity:
            continue
        c = latest.get(po.id)
        if not c or not c.confirmed:
            warnings.append(f"{po.id}: unconfirmed supply excluded")
            continue
        eta = max(po.expected_date, c.promised_date) + timedelta(
            days=scenario.po_delays.get(po.id, 0)
        )
        if eta < data.as_of:
            warnings.append(f"{po.id}: overdue supply excluded")
            continue
        if eta > horizon:
            continue
        key = (po.market_id, po.material_id)
        supplies[key].append([eta, po.quantity - po.received, po.id])
        source_ids[key].extend([po.id, c.id])
        events[key][eta][0] += po.quantity - po.received
    for lots in supplies.values():
        lots.sort(key=lambda x: (x[0], x[2]))
    boms = defaultdict(list)
    for b in data.boms:
        boms[b.phase].append(b)
    requirements = []
    by_plan = defaultdict(list)
    for p in plans:
        # Aggregate duplicate material BOM lines before allocating inventory.
        needs = defaultdict(int)
        bom_ids = defaultdict(list)
        for b in boms[p.phase]:
            needs[b.material_id] += quantity(p.homes, b.units_per_home)
            bom_ids[b.material_id].append(b.id)
        for mid, need in sorted(needs.items()):
            key = (p.market_id, mid)
            due = planned_dates[p.id]
            if key not in snapshots:
                warnings.append(f"{p.market_id}/{mid}: missing inventory snapshot; assumed zero")
            events[key][due][1] += need
            remaining, ontime, last_date = need, 0, None
            used = []
            for lot in supplies[key]:
                take = min(lot[1], remaining)
                if take:
                    lot[1] -= take
                    remaining -= take
                    used.append(lot[2])
                    last_date = lot[0]
                    if lot[0] <= due:
                        ontime += take
                if not remaining:
                    break
            r = Requirement(
                id=f"req-{p.id}-{mid}",
                plan_id=p.id,
                market_id=p.market_id,
                material_id=mid,
                family=materials[mid].family,
                due_date=due,
                quantity=need,
                on_time_quantity=ontime,
                shortage=need - ontime,
                readiness=round(100 * ontime / need, 2),
                material_ready_date=last_date if remaining == 0 else None,
                source_ids=sorted(set([p.id, *bom_ids[mid], *source_ids[key], *used])),
            )
            requirements.append(r)
            by_plan[p.id].append(r)
    phases = {}
    plan_map = {p.id: p for p in plans}

    def resolve(pid: str, visiting: set[str]):
        if pid in phases:
            return phases[pid]
        if pid in visiting:
            raise ValueError("Cyclic dependency")
        p = plan_map[pid]
        due = planned_dates[pid]
        reqs = by_plan[pid]
        ready = [r.material_ready_date for r in reqs]
        unknown = not ready or any(d is None for d in ready)
        start = max([due, *[d for d in ready if d is not None]])
        blockers = [r.id for r in reqs if r.shortage]
        # The binding path follows the gate that actually determines start time.
        # Earlier predecessors with slack are not labelled critical.
        if unknown:
            path = [next((r.id for r in reqs if r.material_ready_date is None), pid), pid]
        elif start > due:
            path = [next(r.id for r in reqs if r.material_ready_date == start), pid]
        else:
            path = [pid]
        if p.predecessor_id:
            if p.predecessor_id not in plan_map:
                unknown = True
                blockers.append(p.predecessor_id)
            else:
                parent = resolve(p.predecessor_id, visiting | {pid})
                if parent.earliest_finish is None:
                    path = [*parent.critical_path, pid]
                    unknown = True
                    blockers.append(p.predecessor_id)
                else:
                    dependency_start = parent.earliest_finish + timedelta(days=1)
                    if dependency_start >= start and not unknown:
                        path = [*parent.critical_path, pid]
                    start = max(start, dependency_start)
                    if dependency_start > due:
                        blockers.append(p.predecessor_id)
        result = PhaseResult(
            plan_id=pid,
            market_id=p.market_id,
            phase=p.phase,
            planned_start=due,
            planned_finish=due + timedelta(days=p.duration_days - 1),
            earliest_start=None if unknown else start,
            earliest_finish=None if unknown else start + timedelta(days=p.duration_days - 1),
            readiness=min((r.readiness for r in reqs), default=0),
            delay_days=None if unknown else (start - due).days,
            blocked_by=blockers,
            critical_path=path,
        )
        phases[pid] = result
        return result

    for p in plans:
        resolve(p.id, set())
    market_results = []
    for m in data.markets:
        reqs = [r for r in requirements if r.market_id == m.id]
        m_phases = [p for p in phases.values() if p.market_id == m.id]
        readiness = min((r.readiness for r in reqs), default=100)
        constraints = [
            p.planned_start for p in m_phases if p.delay_days is None or p.delay_days > 0
        ]
        completion = (
            None
            if any(p.earliest_finish is None for p in m_phases)
            else max((p.earliest_finish for p in m_phases), default=None)
        )
        market_results.append(
            MarketResult(
                market_id=m.id,
                name=m.name,
                region=m.region,
                homes=max((p.homes for p in plans if p.market_id == m.id), default=0),
                readiness=readiness,
                status="At risk" if constraints else "Watch" if readiness < 100 else "Ready",
                earliest_constraint=min(constraints, default=None),
                blockers=sum(r.shortage > 0 for r in reqs),
                families={
                    f: min(r.readiness for r in reqs if r.family == f)
                    for f in sorted({r.family for r in reqs})
                },
                completion=completion,
            )
        )
    ledger = []
    for (market, material), dates in sorted(events.items()):
        dates[horizon]  # End-of-horizon point makes the protected interval explicit.
        balance = 0
        for day, (receipts, demand) in sorted(dates.items()):
            balance += receipts - demand
            ledger.append(
                LedgerPoint(
                    market_id=market,
                    material_id=material,
                    date=day,
                    receipts=receipts,
                    demand=demand,
                    balance=balance,
                )
            )
    timeline = []
    for offset in sorted({*range(0, scenario.horizon_days + 1, 7), scenario.horizon_days}):
        day = data.as_of + timedelta(days=offset)
        begun = [p for p in phases.values() if p.planned_start <= day]
        constrained = sum(p.delay_days is None or p.delay_days > 0 for p in begun)
        completed = [
            p
            for p in phases.values()
            if p.phase == "Activation" and p.earliest_finish and p.earliest_finish <= day
        ]
        timeline.append(
            TimelinePoint(
                date=day,
                ready_phases=len(begun) - constrained,
                constrained_phases=constrained,
                cumulative_homes=sum(plan_map[p.plan_id].homes for p in completed),
            )
        )
    digest = sha256(
        (ALGORITHM_VERSION + data.model_dump_json() + scenario.model_dump_json()).encode()
    ).hexdigest()[:20]
    weights = sum(m.homes for m in market_results)
    return PlanningResult(
        id=f"run-{digest}",
        dataset_id=data.id,
        as_of=data.as_of,
        scenario=scenario,
        readiness=round(sum(m.readiness * m.homes for m in market_results) / weights, 2)
        if weights
        else 100,
        markets=market_results,
        requirements=requirements,
        phases=list(phases.values()),
        ledger=ledger,
        timeline=timeline,
        warnings=sorted(set(warnings)),
    )
