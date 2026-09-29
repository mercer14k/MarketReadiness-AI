export type Market = {
  market_id: string;
  name: string;
  region: string;
  homes: number;
  readiness: number;
  status: "Ready" | "Watch" | "At risk";
  earliest_constraint: string | null;
  blockers: number;
  families: Record<string, number>;
  completion: string | null;
};
export type Requirement = {
  id: string;
  plan_id: string;
  market_id: string;
  material_id: string;
  family: string;
  due_date: string;
  quantity: number;
  on_time_quantity: number;
  shortage: number;
  readiness: number;
  material_ready_date: string | null;
  source_ids: string[];
};
export type Phase = {
  plan_id: string;
  market_id: string;
  phase: string;
  planned_start: string;
  planned_finish: string;
  earliest_start: string | null;
  earliest_finish: string | null;
  readiness: number;
  delay_days: number | null;
  blocked_by: string[];
  critical_path: string[];
};
export type Portfolio = {
  id: string;
  dataset_id: string;
  algorithm_version: string;
  as_of: string;
  readiness: number;
  markets: Market[];
  requirements: Requirement[];
  phases: Phase[];
  ledger: {
    market_id: string;
    material_id: string;
    date: string;
    receipts: number;
    demand: number;
    balance: number;
  }[];
  timeline: {
    date: string;
    ready_phases: number;
    constrained_phases: number;
    cumulative_homes: number;
  }[];
  warnings: string[];
  scenario: { name: string; horizon_days: number };
};
export type Transfer = {
  id: string;
  material_id: string;
  from_market: string;
  to_market: string;
  quantity: number;
  arrival_date: string;
  need_date: string;
  donor_min_balance_after: number;
  safety_stock: number;
  source_ids: string[];
};
export type Brief = {
  id: string;
  period: string;
  mode: string;
  headline: string;
  statements: { id: string; text: string; source_ids: string[] }[];
  telemetry: Record<string, unknown>;
};
export type Validation = {
  id: string;
  accepted: boolean;
  dataset_id: string;
  checked_records: number;
  issues: {
    table: string;
    record_id: string;
    severity: string;
    message: string;
  }[];
};
export type RawRow = Record<string, unknown>;
export type Page = {
  items: RawRow[];
  total: number;
  offset: number;
  limit: number;
};
export type ForecastSeries = {
  market_id: string;
  material_id: string;
  status: string;
  mae?: number;
  wape?: number | null;
  training_observations?: number;
  prediction?: { date: string; quantity: number }[];
};
export type Forecast = {
  model: string;
  status: string;
  wape?: number;
  backtest_observations?: number;
  series: ForecastSeries[];
};
