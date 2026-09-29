from datetime import date

import pytest
from marketreadiness.data.generator import generate
from marketreadiness.domain.planning import plan, quantity
from marketreadiness.domain.schemas import Scenario
from marketreadiness.domain.transfers import recommend


def test_readiness_and_constraint_ground_truth(tiny):
    result = plan(tiny)
    north = result.markets[0]
    assert north.readiness == 40
    assert north.earliest_constraint == date(2026, 1, 10)
    assert result.phases[0].earliest_start == date(2026, 1, 15)
    assert result.phases[0].earliest_finish == date(2026, 1, 19)
    assert result.phases[0].delay_days == 5
    assert result.readiness == 70
    assert result.requirements[0].shortage == 60


def test_same_day_receipts_count(tiny):
    tiny.purchase_orders[0].expected_date = date(2026, 1, 10)
    tiny.commitments[0].promised_date = date(2026, 1, 10)
    assert plan(tiny).markets[0].readiness == 100


def test_unconfirmed_supply_is_excluded(tiny):
    tiny.commitments[0].confirmed = False
    result = plan(tiny)
    assert result.phases[0].earliest_start is None
    assert "unconfirmed" in result.warnings[0]


def test_overdue_supply_is_not_assumed_available(tiny):
    tiny.purchase_orders[0].expected_date = date(2025, 12, 25)
    tiny.commitments[0].promised_date = date(2025, 12, 25)
    assert plan(tiny).phases[0].earliest_start is None


def test_partial_receipt_not_double_counted(tiny):
    tiny.purchase_orders[0].received = 20
    result = plan(tiny)
    assert result.requirements[0].material_ready_date is None
    assert sum(p.receipts for p in result.ledger if p.market_id == "north") == 80


def test_cancelled_po_excluded(tiny):
    tiny.purchase_orders[0].status = "cancelled"
    assert plan(tiny).phases[0].earliest_start is None


def test_quarantine_and_reservation_excluded(tiny):
    tiny.inventory[0].quarantined = 10
    tiny.inventory[0].reserved = 5
    assert plan(tiny).markets[0].readiness == 25


def test_missing_stock_reported_and_zero_assumed(tiny):
    tiny.inventory = tiny.inventory[1:]
    result = plan(tiny)
    assert result.markets[0].readiness == 0
    assert any("missing inventory" in w for w in result.warnings)


def test_scenario_isolation(tiny):
    original = tiny.model_dump_json()
    baseline = plan(tiny)
    scenario = plan(tiny, Scenario(name="delay", po_delays={"po": 20}, accelerate_days=3))
    assert tiny.model_dump_json() == original
    assert scenario.phases[0].earliest_start == date(2026, 2, 4)
    assert baseline.phases[0].earliest_start == date(2026, 1, 15)
    assert scenario.id != baseline.id


def test_unknown_scenario_target_rejected(tiny):
    with pytest.raises(ValueError):
        plan(tiny, Scenario(po_delays={"unknown": 1}))


def test_fixed_seed_is_reproducible():
    assert generate(42).model_dump_json() == generate(42).model_dump_json()
    assert generate(41).model_dump_json() != generate(42).model_dump_json()


def test_integer_rounding_uses_decimal():
    assert quantity(100, 0.01) == 1
    assert quantity(101, 0.01) == 2
    assert quantity(100, 0.07) == 7


def test_delays_propagate_to_successor(demo):
    result = plan(demo)
    fiber = next(p for p in result.phases if p.plan_id == "plan-m00-00-1")
    activation = next(p for p in result.phases if p.plan_id == "plan-m00-00-2")
    assert fiber.delay_days == 10
    assert activation.delay_days == 7
    assert activation.critical_path == ["req-plan-m00-00-1-fiber", "plan-m00-00-1", "plan-m00-00-2"]


def test_conservation_across_repeated_demands(tiny):
    second = tiny.plans[0].model_copy(update={"id": "build-north-2", "start": date(2026, 1, 20)})
    tiny.plans.append(second)
    result = plan(tiny)
    reqs = [r for r in result.requirements if r.market_id == "north"]
    assert sum(r.on_time_quantity for r in reqs) == 40
    assert reqs[1].material_ready_date is None


def test_transfer_conservation_and_floor(tiny):
    recs = recommend(tiny, plan(tiny))
    assert len(recs) == 1
    assert recs[0].quantity == 60
    assert recs[0].donor_min_balance_after == 40
    assert recs[0].safety_stock == 10
    assert recs[0].arrival_date <= recs[0].need_date


def test_transfer_donor_not_overallocated(tiny):
    tiny.plans.append(tiny.plans[0].model_copy(update={"id": "later", "start": date(2026, 1, 20)}))
    recs = recommend(tiny, plan(tiny))
    assert sum(t.quantity for t in recs) == 90
    assert all(t.donor_min_balance_after >= t.safety_stock for t in recs)


def test_transfer_guardrails(tiny):
    from marketreadiness.domain.schemas import Guardrails

    assert not recommend(tiny, plan(tiny), Guardrails(transit_days=20))
    assert not recommend(tiny, plan(tiny), Guardrails(reserve_multiplier=10))
    tiny.markets[1].region = "West"
    assert not recommend(tiny, plan(tiny), Guardrails(same_region_only=True))


def test_forecast_backtest_and_no_leakage(demo):
    from marketreadiness.domain.forecast import forecast

    before = plan(demo).model_dump()
    result = forecast(demo)
    assert result["status"] == "ok"
    assert len(result["series"]) == 84
    assert result["backtest_observations"] == 1176
    assert result["wape"] < 0.15
    assert plan(demo).model_dump() == before


def test_forecast_missing_evidence(tiny):
    from marketreadiness.domain.forecast import forecast, weekday_mean

    assert forecast(tiny)["status"] == "insufficient_evidence"
    with pytest.raises(ValueError):
        weekday_mean([], [date(2026, 1, 1)])


def test_horizon_includes_last_day(tiny):
    from datetime import timedelta

    result = plan(tiny, Scenario(horizon_days=10))
    assert result.timeline[-1].date == tiny.as_of + timedelta(days=10)


def test_ready_phase_release_has_no_false_critical_predecessor(demo):
    result = plan(demo)
    phase = next(p for p in result.phases if p.plan_id == "plan-m00-01-2")
    assert phase.critical_path == ["plan-m00-01-2"]
