from datetime import UTC, date, datetime

import pytest
from marketreadiness.data.generator import generate
from marketreadiness.domain.schemas import Dataset


@pytest.fixture
def demo():
    return generate()


@pytest.fixture
def tiny():
    stamp = datetime(2026, 1, 1, tzinfo=UTC)

    def row(id, **kwargs):
        return dict(id=id, source_id="test", ingested_at=stamp, **kwargs)

    return Dataset.model_validate(
        dict(
            id="test",
            as_of=date(2026, 1, 1),
            seed=1,
            markets=[
                row("north", name="North", region="East", priority=5),
                row("south", name="South", region="East", priority=3),
            ],
            materials=[row("fiber", name="Fiber", family="Fiber", unit="m", safety_stock=10)],
            boms=[row("bom", phase="Fiber placement", material_id="fiber", units_per_home=1)],
            plans=[
                row(
                    "build-north",
                    market_id="north",
                    phase="Fiber placement",
                    homes=100,
                    start="2026-01-10",
                    duration_days=5,
                ),
                row(
                    "build-south",
                    market_id="south",
                    phase="Fiber placement",
                    homes=100,
                    start="2026-01-12",
                    duration_days=5,
                ),
            ],
            inventory=[
                row(
                    "inv-north",
                    market_id="north",
                    material_id="fiber",
                    quantity=40,
                    snapshot_date="2026-01-01",
                ),
                row(
                    "inv-south",
                    market_id="south",
                    material_id="fiber",
                    quantity=200,
                    snapshot_date="2026-01-01",
                ),
            ],
            purchase_orders=[
                row(
                    "po",
                    market_id="north",
                    material_id="fiber",
                    supplier="FiberCo",
                    quantity=60,
                    expected_date="2026-01-15",
                )
            ],
            commitments=[
                row(
                    "commit",
                    po_id="po",
                    promised_date="2026-01-15",
                    confirmed=True,
                    updated_at=stamp,
                )
            ],
            consumption=[],
        )
    )
