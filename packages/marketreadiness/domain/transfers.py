"""Conservative, stock-conserving transfer recommendations, never execution."""

from collections import defaultdict
from datetime import timedelta
from math import ceil

from marketreadiness.domain.schemas import Dataset, Guardrails, PlanningResult, Transfer


def recommend(
    data: Dataset, result: PlanningResult, guardrails: Guardrails | None = None
) -> list[Transfer]:
    g = guardrails or Guardrails()
    mats = {m.id: m for m in data.materials}
    markets = {m.id: m for m in data.markets}
    readiness = {m.market_id: m.readiness for m in result.markets}
    available = defaultdict(int)
    inv_ids = defaultdict(list)
    for inv in data.inventory:
        key = inv.market_id, inv.material_id
        available[key] += inv.quantity - inv.reserved - inv.quarantined
        inv_ids[key].append(inv.id)
    minimum = {}
    for point in result.ledger:
        key = point.market_id, point.material_id
        minimum[key] = min(minimum.get(key, point.balance), point.balance)
    remaining = {}
    for key, stock in available.items():
        reserve = ceil(mats[key[1]].safety_stock * g.reserve_multiplier)
        remaining[key] = max(0, min(stock - reserve, minimum.get(key, 0) - reserve))
    transferred = defaultdict(int)
    recs = []
    arrival = data.as_of + timedelta(days=g.transit_days)
    for req in sorted(
        result.requirements, key=lambda r: (r.due_date, -markets[r.market_id].priority, r.id)
    ):
        need = req.shortage
        if not need or arrival > req.due_date:
            continue
        donors = sorted(
            (k for k in remaining if k[1] == req.material_id and k[0] != req.market_id),
            key=lambda k: (-remaining[k], k),
        )
        for key in donors:
            if (
                readiness[key[0]] < g.min_donor_readiness
                or readiness[key[0]] <= readiness[req.market_id]
            ):
                continue
            if g.same_region_only and markets[key[0]].region != markets[req.market_id].region:
                continue
            qty = min(need, remaining[key], g.max_transfer)
            if qty <= 0:
                continue
            remaining[key] -= qty
            need -= qty
            transferred[key] += qty
            reserve = ceil(mats[req.material_id].safety_stock * g.reserve_multiplier)
            recs.append(
                Transfer(
                    id=f"transfer-{len(recs) + 1}",
                    material_id=req.material_id,
                    from_market=key[0],
                    to_market=req.market_id,
                    quantity=qty,
                    arrival_date=arrival,
                    need_date=req.due_date,
                    donor_min_balance_after=minimum[key] - transferred[key],
                    safety_stock=reserve,
                    source_ids=[*inv_ids[key], req.id, result.id],
                )
            )
            if need == 0:
                break
    return recs
