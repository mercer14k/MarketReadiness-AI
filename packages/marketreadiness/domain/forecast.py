"""Interpretable weekday-mean forecast with a strictly held-out backtest.

Historical consumption is already reflected in the as-of inventory snapshot.
Forecasts are diagnostic and are never added to BOM demand a second time.
"""

from datetime import timedelta
from statistics import mean

import polars as pl

from marketreadiness.domain.schemas import Dataset


def weekday_mean(history: list[tuple], future: list) -> list[float]:
    if not history:
        raise ValueError("Missing consumption evidence")
    overall = mean(q for _, q in history)
    groups = {d: [q for day, q in history if day.weekday() == d] for d in range(7)}
    return [round(mean(groups[d.weekday()]) if groups[d.weekday()] else overall, 2) for d in future]


def forecast(data: Dataset) -> dict:
    if not data.consumption:
        return {"model": "weekday-mean-v1", "status": "insufficient_evidence", "series": []}
    frame = pl.DataFrame(
        [
            {"market": c.market_id, "material": c.material_id, "day": c.date, "qty": c.quantity}
            for c in data.consumption
        ]
    )
    grouped = frame.group_by(["market", "material", "day"]).agg(pl.col("qty").sum()).sort("day")
    output = []
    total_error = total_actual = n = 0
    for key, group in grouped.partition_by(["market", "material"], as_dict=True).items():
        history = [(r["day"], r["qty"]) for r in group.to_dicts()]
        # Missing days are unknown observations, not silently assumed zeros.
        if len(history) < 28 or history[-1][0] != data.as_of - timedelta(days=1):
            output.append(
                {"market_id": key[0], "material_id": key[1], "status": "insufficient_evidence"}
            )
            continue
        train, test = history[:-14], history[-14:]
        pred = weekday_mean(train, [d for d, _ in test])
        error = sum(abs(actual - p) for (_, actual), p in zip(test, pred, strict=True))
        actual = sum(q for _, q in test)
        total_error += error
        total_actual += actual
        n += len(test)
        days = [data.as_of + timedelta(days=i) for i in range(14)]
        values = weekday_mean(history, days)
        output.append(
            {
                "market_id": key[0],
                "material_id": key[1],
                "status": "ok",
                "mae": round(error / 14, 3),
                "wape": round(error / actual, 4) if actual else None,
                "training_observations": len(history),
                "prediction": [
                    {"date": d.isoformat(), "quantity": q}
                    for d, q in zip(days, values, strict=True)
                ],
            }
        )
    return {
        "model": "weekday-mean-v1",
        "status": "ok" if n else "insufficient_evidence",
        "mae": round(total_error / n, 3) if n else None,
        "wape": round(total_error / total_actual, 4) if total_actual else None,
        "backtest_observations": n,
        "series": output,
        "note": "Diagnostic forecast; not added to scheduled BOM requirements. MAE pools different units; use per-material errors.",
    }
