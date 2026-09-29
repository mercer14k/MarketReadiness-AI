"""Reproducible infrastructure portfolio with documented stress cases."""

import argparse
import random
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from marketreadiness.domain.schemas import Dataset

MARKETS = [
    ("Austin", "South"),
    ("Dallas", "South"),
    ("Houston", "South"),
    ("San Antonio", "South"),
    ("Phoenix", "West"),
    ("Denver", "West"),
    ("Las Vegas", "West"),
    ("Portland", "West"),
    ("Nashville", "East"),
    ("Charlotte", "East"),
    ("Raleigh", "East"),
    ("Columbus", "Central"),
    ("Indianapolis", "Central"),
    ("Kansas City", "Central"),
]
MATERIALS = [
    ("duct", "HDPE conduit", "Civil", "m", 120, 8.0),
    ("vault", "Handhole vault", "Civil", "each", 2, 0.04),
    ("fiber", "144-count fiber", "Fiber", "m", 150, 12.0),
    ("splice", "Splice enclosure", "Connectivity", "each", 2, 0.05),
    ("olt", "Optical line terminal", "Electronics", "each", 1, 0.01),
    ("ont", "Optical network terminal", "Electronics", "each", 10, 1.0),
]
PHASES = ["Civil works", "Fiber placement", "Activation"]


def generate(seed: int = 42, scale: int = 1) -> Dataset:
    if not 1 <= scale <= 100:
        raise ValueError("scale must be 1..100")
    rng = random.Random(seed)
    as_of = date(2026, 9, 28)
    stamp = datetime(2026, 9, 28, tzinfo=UTC)
    dataset_id = f"fiber-demo-s{seed}-x{scale}"

    def meta(id):
        return dict(
            id=id,
            source_id=dataset_id,
            ingested_at=stamp,
            validation_status="valid",
            lineage={"generator": "1.0", "seed": str(seed)},
        )

    raw = dict(
        id=dataset_id,
        as_of=as_of,
        seed=seed,
        markets=[],
        materials=[],
        boms=[],
        plans=[],
        inventory=[],
        purchase_orders=[],
        commitments=[],
        consumption=[],
    )
    for mid, name, family, unit, safety, rate in MATERIALS:
        raw["materials"].append(
            dict(**meta(mid), name=name, family=family, unit=unit, safety_stock=safety)
        )
        phase = PHASES[0 if mid in ("duct", "vault") else 1 if mid in ("fiber", "splice") else 2]
        raw["boms"].append(
            dict(**meta(f"bom-{mid}"), phase=phase, material_id=mid, units_per_home=rate)
        )
    for batch in range(scale):
        for i, (name, region) in enumerate(MARKETS):
            market = f"m{batch:02d}-{i:02d}"
            homes = rng.randrange(300, 900, 50)
            start = 5 + (i % 5) * 2
            raw["markets"].append(
                dict(
                    **meta(market),
                    name=name if not batch else f"{name} {batch + 1}",
                    region=region,
                    priority=5 if i in (0, 4, 9) else 3,
                )
            )
            for j, phase in enumerate(PHASES):
                raw["plans"].append(
                    dict(
                        **meta(f"plan-{market}-{j}"),
                        market_id=market,
                        phase=phase,
                        homes=homes,
                        start=as_of + timedelta(days=start + j * 15),
                        duration_days=12,
                        predecessor_id=f"plan-{market}-{j - 1}" if j else None,
                    )
                )
            for k, (mid, _, _, _, _, rate) in enumerate(MATERIALS):
                import math

                need = math.ceil(homes * rate)
                phase_idx = 0 if k < 2 else 1 if k < 4 else 2
                due = as_of + timedelta(days=start + phase_idx * 15)
                # Donors have surplus. Other markets depend on incoming supply.
                donor = i in (1, 3, 7, 10, 13)
                fraction = 1.5 if donor else rng.choice([0.45, 0.65, 0.85])
                stock = math.ceil(need * fraction)
                quarantine = min(stock, math.ceil(need * 0.18)) if i == 4 and mid == "fiber" else 0
                raw["inventory"].append(
                    dict(
                        **meta(f"inv-{market}-{mid}"),
                        market_id=market,
                        material_id=mid,
                        quantity=stock,
                        reserved=0,
                        quarantined=quarantine,
                        snapshot_date=as_of,
                    )
                )
                qty = max(0, need - stock) + math.ceil(need * 0.20)
                late = (
                    (i == 0 and mid == "fiber")
                    or (i == 4 and mid == "fiber")
                    or (i == 9 and mid == "ont")
                )
                unconfirmed = i == 6 and mid == "olt"
                overdue = i == 11 and mid == "splice"
                eta = as_of - timedelta(days=3) if overdue else due - timedelta(days=2)
                po = f"po-{market}-{mid}"
                raw["purchase_orders"].append(
                    dict(
                        **meta(po),
                        market_id=market,
                        material_id=mid,
                        supplier=["Northline Fiber", "TerraWorks Supply", "Lumen Components"][
                            k % 3
                        ],
                        quantity=qty,
                        received=0,
                        expected_date=eta,
                        status="open",
                    )
                )
                raw["commitments"].append(
                    dict(
                        **meta(f"commit-{po}"),
                        po_id=po,
                        promised_date=eta + timedelta(days=12 if late else 0),
                        confirmed=not unconfirmed,
                        updated_at=stamp,
                    )
                )
                for day in range(56):
                    weekday = (as_of - timedelta(days=56 - day)).weekday()
                    daily = max(
                        0,
                        round(
                            need / 30 * (1.2 if weekday < 5 else 0.35)
                            + rng.gauss(0, max(1, need / 300))
                        ),
                    )
                    raw["consumption"].append(
                        dict(
                            **meta(f"use-{market}-{mid}-{day}"),
                            market_id=market,
                            material_id=mid,
                            date=as_of - timedelta(days=56 - day),
                            quantity=daily,
                        )
                    )
    return Dataset.model_validate(raw)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--scale", type=int, default=1)
    parser.add_argument("--output", type=Path, default=Path("data/sample/portfolio.json"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(generate(args.seed, args.scale).model_dump_json(indent=2) + "\n")
    print(args.output)


if __name__ == "__main__":
    main()
