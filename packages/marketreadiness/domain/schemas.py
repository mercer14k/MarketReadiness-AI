"""Contracts shared by ingestion, planning, storage and HTTP boundaries."""

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ID = Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_.:-]+$")]
Qty = Annotated[int, Field(ge=0, le=1_000_000_000, strict=True)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Record(Contract):
    id: ID
    source_id: ID
    ingested_at: datetime
    validation_status: Literal["valid", "warning"] = "valid"
    lineage: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def timezone_required(self):
        if self.ingested_at.tzinfo is None:
            raise ValueError("ingested_at must include a timezone")
        return self


class Market(Record):
    name: str = Field(min_length=1, max_length=100)
    region: str = Field(min_length=1, max_length=40)
    priority: int = Field(ge=1, le=5)


class Material(Record):
    name: str = Field(min_length=1, max_length=100)
    family: Literal["Fiber", "Civil", "Electronics", "Connectivity"]
    unit: str = Field(min_length=1, max_length=20)
    safety_stock: Qty


class BOM(Record):
    phase: Literal["Civil works", "Fiber placement", "Activation"]
    material_id: ID
    units_per_home: float = Field(gt=0, le=100, allow_inf_nan=False)


class BuildPlan(Record):
    market_id: ID
    phase: Literal["Civil works", "Fiber placement", "Activation"]
    homes: int = Field(gt=0, le=100_000)
    start: date
    duration_days: int = Field(ge=1, le=180)
    predecessor_id: ID | None = None


class Inventory(Record):
    market_id: ID
    material_id: ID
    quantity: Qty
    reserved: Qty = 0
    quarantined: Qty = 0
    snapshot_date: date

    @model_validator(mode="after")
    def usable_nonnegative(self):
        if self.reserved + self.quarantined > self.quantity:
            raise ValueError("reserved + quarantined exceeds quantity")
        return self


class PurchaseOrder(Record):
    market_id: ID
    material_id: ID
    supplier: str = Field(min_length=1, max_length=100)
    quantity: Qty
    received: Qty = 0
    expected_date: date
    status: Literal["open", "cancelled", "closed"] = "open"

    @model_validator(mode="after")
    def received_not_above_order(self):
        if self.received > self.quantity:
            raise ValueError("received exceeds ordered quantity")
        return self


class Commitment(Record):
    po_id: ID
    promised_date: date
    confirmed: bool
    updated_at: datetime


class Consumption(Record):
    market_id: ID
    material_id: ID
    date: date
    quantity: Qty


class Dataset(Contract):
    id: ID
    schema_version: Literal["1.0"] = "1.0"
    as_of: date
    seed: int
    markets: list[Market] = Field(min_length=1, max_length=2000)
    materials: list[Material] = Field(min_length=1, max_length=100)
    boms: list[BOM] = Field(min_length=1, max_length=300)
    plans: list[BuildPlan] = Field(min_length=1, max_length=12000)
    inventory: list[Inventory] = Field(max_length=200000)
    purchase_orders: list[PurchaseOrder] = Field(max_length=200000)
    commitments: list[Commitment] = Field(max_length=200000)
    consumption: list[Consumption] = Field(max_length=1000000)


class Scenario(Contract):
    name: str = Field(default="Baseline", min_length=1, max_length=100)
    po_delays: dict[ID, Annotated[int, Field(ge=0, le=180)]] = Field(default_factory=dict)
    accelerate_days: int = Field(default=0, ge=0, le=60)
    market_ids: list[ID] = Field(default_factory=list, max_length=2000)
    horizon_days: int = Field(default=90, ge=7, le=365)


class Guardrails(Contract):
    min_donor_readiness: float = Field(default=100, ge=0, le=100)
    reserve_multiplier: float = Field(default=1, ge=0, le=10)
    transit_days: int = Field(default=3, ge=1, le=30)
    same_region_only: bool = False
    max_transfer: int = Field(default=100000, ge=1, le=1000000)


class ValidationIssue(Contract):
    table: str
    record_id: str | None = None
    field: str = ""
    severity: Literal["error", "warning"]
    message: str


class ValidationReport(Contract):
    id: str
    accepted: bool
    dataset_id: str | None
    checked_records: int
    issues: list[ValidationIssue]


class Requirement(Contract):
    id: str
    plan_id: str
    market_id: str
    material_id: str
    family: str
    due_date: date
    quantity: int
    on_time_quantity: int
    shortage: int
    readiness: float
    material_ready_date: date | None
    source_ids: list[str]


class PhaseResult(Contract):
    plan_id: str
    market_id: str
    phase: str
    planned_start: date
    planned_finish: date
    earliest_start: date | None
    earliest_finish: date | None
    readiness: float
    delay_days: int | None
    blocked_by: list[str]
    critical_path: list[str]


class MarketResult(Contract):
    market_id: str
    name: str
    region: str
    homes: int
    readiness: float
    status: Literal["Ready", "Watch", "At risk"]
    earliest_constraint: date | None
    blockers: int
    families: dict[str, float]
    completion: date | None


class LedgerPoint(Contract):
    market_id: str
    material_id: str
    date: date
    receipts: int
    demand: int
    balance: int


class TimelinePoint(Contract):
    date: date
    ready_phases: int
    constrained_phases: int
    cumulative_homes: int


class PlanningResult(Contract):
    id: str
    dataset_id: str
    algorithm_version: str = "mrp-1.0"
    as_of: date
    scenario: Scenario
    readiness: float
    markets: list[MarketResult]
    requirements: list[Requirement]
    phases: list[PhaseResult]
    ledger: list[LedgerPoint]
    timeline: list[TimelinePoint]
    warnings: list[str]


class Transfer(Contract):
    id: str
    material_id: str
    from_market: str
    to_market: str
    quantity: int
    arrival_date: date
    need_date: date
    donor_min_balance_after: int
    safety_stock: int
    source_ids: list[str]


class Evidence(Contract):
    id: str
    text: str
    source_ids: list[str]


class BriefSelection(Contract):
    evidence_ids: list[str] = Field(max_length=12)
    posture: Literal["ready", "attention", "abstain"]


class Brief(Contract):
    id: str
    period: Literal["daily", "weekly"]
    mode: Literal["deterministic", "local-llm", "fallback", "abstained"]
    headline: str
    statements: list[Evidence]
    telemetry: dict


class MarketDetail(Contract):
    market: MarketResult
    requirements: list[Requirement]
    phases: list[PhaseResult]
    ledger: list[LedgerPoint]


class PredictionPoint(Contract):
    date: date
    quantity: float


class ForecastSeries(Contract):
    market_id: str
    material_id: str
    status: Literal["ok", "insufficient_evidence"]
    mae: float | None = None
    wape: float | None = None
    training_observations: int | None = None
    prediction: list[PredictionPoint] | None = None


class ForecastResult(Contract):
    model: str
    status: Literal["ok", "insufficient_evidence"]
    mae: float | None = None
    wape: float | None = None
    backtest_observations: int | None = None
    series: list[ForecastSeries]
    note: str | None = None


class MarketComparison(Contract):
    market_id: str
    name: str
    baseline: float
    scenario: float
    delta: float
    baseline_constraint: date | None
    scenario_constraint: date | None


class ComparisonResult(Contract):
    baseline_id: str
    scenario_id: str
    readiness_delta: float
    markets: list[MarketComparison]


class SavedScenario(Contract):
    id: str
    name: str
    readiness: float
    dataset_id: str


class ConfigResponse(Contract):
    mode: Literal["demo", "secured"]
    llm_provider: Literal["none", "ollama"]
    version: str
    upload_limit_bytes: int


class ErrorDetail(Contract):
    code: str
    message: str
    trace_id: str | None = None
    details: list[dict] | None = None


class ErrorEnvelope(Contract):
    error: ErrorDetail
