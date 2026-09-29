# Data model and dictionary

Machine-readable contract: [dataset.schema.json](../data/schemas/dataset.schema.json). Stable demonstration: [portfolio.json](../data/sample/portfolio.json). Business validation runs after Pydantic validation and reports all detected errors; invalid rows are never silently skipped.

## Record envelope

All imported source records carry `id` (unique across the whole snapshot), `source_id`, timezone-aware `ingested_at`, `validation_status` (`valid` or `warning`), and optional string-to-string `lineage`. These fields describe source provenance. The database also records the actual document acceptance timestamp. Validation reports hold rejected record IDs, fields, severity and messages, rather than publishing the entire invalid payload.

Derived results contain a stable content-addressed run ID, dataset ID, algorithm version, as-of date and scenario parameters. Requirements carry the exact supporting source IDs. Identical validated input, algorithm version and scenario yield the same result ID. Changing algorithm behavior requires a version bump before a release.

## Tables

| Table | Meaning | Main fields and units |
|---|---|---|
| markets | Deployment markets and planning priority | name; region; priority 1–5 (5 is highest) |
| materials | SKU/family definitions | family; unit; integer safety_stock |
| boms | Phase material per home | phase; material_id; positive units_per_home |
| plans | One cohort per market and phase | homes; start; duration_days; optional predecessor_id |
| inventory | Physical as-of market/SKU stock | quantity; reserved; quarantined; snapshot_date |
| purchase_orders | Open procurement balance | quantity; received; expected_date; supplier; status |
| commitments | Supplier promise revisions | po_id; promised_date; confirmed; updated_at |
| consumption | Historical material usage | date before as_of; integer quantity; market_id; material_id |

Dataset-level fields: `id`, `schema_version=1.0`, `as_of`, `seed`, and the eight record collections. Seed is provenance for generated data and can be 0 for an external source.

## Validation rules

Identifiers use a bounded safe character set. Unknown fields, negative quantities, non-finite numbers, fractional integer units and reserved-plus-quarantine above physical quantity are rejected. Received quantity cannot exceed the order. Foreign keys must resolve. Plan dependency graphs must be acyclic and stay within one market. Inventory snapshots must match the planning date. Future history is rejected to prevent leakage. Commitment updates must be timezone-aware and known as of the planning date. Multiple home cohorts in one market are rejected; use separate market IDs until a project/cohort entity is added.

Quarantined stock and overdue receipts produce visible warnings. Missing inventory is assumed zero and surfaced in planning warnings. A missing BOM rejects ingestion. Missing or unconfirmed commitments exclude incoming supply and produce planning warnings. Exact duplicates are rejected rather than deduplicated implicitly.

## Seed 42 fixture

14 markets, 6 materials, 3 phases, 42 plans, 84 inventory balances, 84 POs, 84 commitments, 56 days of consumption per market/material. Total: **5,024 source records**.

| Seeded condition | Evidence | Expected effect |
|---|---|---|
| Austin late fiber | `commit-po-m00-00-fiber` | Fiber start constrained Oct 18; activation inherits delay |
| Phoenix quarantine + late supply | `inv-m00-04-fiber` | Stock excluded; supply remains insufficient in horizon |
| Las Vegas unconfirmed electronics | `commit-po-m00-06-olt` | OLT receipt excluded |
| Charlotte late ONTs | `commit-po-m00-09-ont` | Activation constrained Nov 10 |
| Columbus overdue enclosure receipt | `po-m00-11-splice` | Shipment not treated as available stock |

The [ground-truth file](../data/sample/ground-truth.json) is a hand-reviewed regression oracle, not an estimate of real-world predictive performance. Invalid fixtures are constructed in tests and shown in rejected import reports when submitted through the app.

## Larger datasets

```bash
python -m marketreadiness.data.generator --seed 42 --scale 10 --output data/generated/large.json
```

Scale multiplies the 14-market template with independent deterministic RNG draws and distinct IDs. Scale 10 gives 140 markets and 50,132 records. The generated file may exceed the HTTP import limit at larger scales; benchmark it directly rather than increasing an upload limit without resource analysis.
