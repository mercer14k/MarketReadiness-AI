import { useCallback, useEffect, useState } from "react";
import {
  ArrowDownToLine,
  ArrowLeftRight,
  Check,
  Database,
  FileText,
  FlaskConical,
  Play,
  ShieldCheck,
  Upload,
} from "lucide-react";
import {
  dateLabel,
  materialNames,
  materialUnits,
  percent,
  request,
  saveFile,
} from "./api";
import { Empty, ErrorMessage, Label, Loading, Modal } from "./components";
import { Chart, chartTheme } from "./Chart";
import type {
  Brief,
  Forecast,
  Page,
  Portfolio,
  RawRow,
  Transfer,
  Validation,
} from "./types";

function Heading({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <div className="page-heading">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>
          {title}
          <span className="heading-dot">.</span>
        </h1>
        <p>{description}</p>
      </div>
    </div>
  );
}

export function ScenarioView({ data }: { data: Portfolio }) {
  const [name, setName] = useState("Supply delay + accelerated build");
  const [orders, setOrders] = useState<RawRow[]>([]);
  const [po, setPo] = useState("po-m00-00-fiber");
  const [days, setDays] = useState(14);
  const [acceleration, setAcceleration] = useState(5);
  const [market, setMarket] = useState("");
  const [result, setResult] = useState<Portfolio | null>(null);
  const [saved, setSaved] = useState<
    { id: string; name: string; dataset_id: string }[]
  >([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const loadSaved = useCallback(
    () => request<typeof saved>("/scenarios").then(setSaved),
    [],
  );
  useEffect(() => {
    void Promise.all([
      request<Page>("/records/purchase_orders?limit=500").then((p) => {
        setOrders(p.items);
        if (!p.items.some((x) => x.id === "po-m00-00-fiber"))
          setPo(String(p.items[0]?.id || ""));
      }),
      loadSaved(),
    ]).catch((e) => setError(e.message));
  }, [loadSaved]);
  async function run() {
    setBusy(true);
    setError("");
    try {
      const r = await request<Portfolio>(
        "/scenarios",
        {
          name,
          po_delays: po ? { [po]: days } : {},
          accelerate_days: acceleration,
          market_ids: market ? [market] : [],
          horizon_days: 90,
        },
        true,
      );
      setResult(r);
      await loadSaved();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Heading
        eyebrow="DECISION WORKSPACE / SIMULATION"
        title="Scenario lab"
        description="Stress-test supply and construction changes against the same baseline."
      />
      {error && <ErrorMessage message={error} />}
      <div className="scenario-layout">
        <section className="panel form-panel">
          <div className="panel-heading">
            <h2>
              <FlaskConical size={19} /> Scenario controls
            </h2>
            <Label>ISOLATED</Label>
          </div>
          <label>
            Scenario name
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={100}
            />
          </label>
          <label>
            Delay purchase order
            <select value={po} onChange={(e) => setPo(e.target.value)}>
              <option value="">No PO delay</option>
              {orders.map((o) => (
                <option key={String(o.id)} value={String(o.id)}>
                  {data.markets.find((m) => m.market_id === o.market_id)
                    ?.name || String(o.market_id)}{" "}
                  ·{" "}
                  {materialNames[String(o.material_id)] ||
                    String(o.material_id)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Supply delay <strong>{days} days</strong>
            <input
              type="range"
              min="0"
              max="60"
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
            />
          </label>
          <div className="form-divider" />
          <label>
            Accelerate construction <strong>{acceleration} days</strong>
            <input
              type="range"
              min="0"
              max="30"
              value={acceleration}
              onChange={(e) => setAcceleration(Number(e.target.value))}
            />
          </label>
          <label>
            Apply acceleration to
            <select value={market} onChange={(e) => setMarket(e.target.value)}>
              <option value="">All markets</option>
              {data.markets.map((m) => (
                <option key={m.market_id} value={m.market_id}>
                  {m.name}
                </option>
              ))}
            </select>
          </label>
          <button
            className="primary full"
            onClick={() => void run()}
            disabled={busy || !name.trim()}
          >
            <Play size={16} />
            {busy ? "Calculating…" : "Run comparison"}
          </button>
          <p className="mini-note">
            Scenarios are immutable snapshots. Running a scenario never changes
            inventory or purchase orders.
          </p>
        </section>
        <div>
          <section className="panel comparison">
            <div className="panel-heading">
              <h2>Baseline vs. scenario</h2>
              <Label>COMPUTED</Label>
            </div>
            {!result ? (
              <Empty>
                <FlaskConical size={32} />
                <h3>Explore the cost of a change</h3>
                <p>
                  Adjust the controls and run a comparison to see which markets
                  and constraint dates move.
                </p>
              </Empty>
            ) : (
              <>
                <div className="comparison-scores">
                  <div>
                    <span>Baseline</span>
                    <strong>{percent(data.readiness)}</strong>
                  </div>
                  <div>
                    <span>{result.scenario.name}</span>
                    <strong className="amber-text">
                      {percent(result.readiness)}
                    </strong>
                  </div>
                  <div>
                    <span>Change</span>
                    <strong
                      className={
                        result.readiness < data.readiness
                          ? "red-text"
                          : "teal-text"
                      }
                    >
                      {(result.readiness - data.readiness).toFixed(1)}
                      <small> pp</small>
                    </strong>
                  </div>
                </div>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Market</th>
                        <th>Baseline</th>
                        <th>Scenario</th>
                        <th>Constraint change</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.markets.map((m) => {
                        const baseline = data.markets.find(
                          (b) => b.market_id === m.market_id,
                        )!;
                        return (
                          <tr key={m.market_id}>
                            <td>{m.name}</td>
                            <td>{percent(baseline.readiness)}</td>
                            <td
                              className={
                                m.readiness < baseline.readiness
                                  ? "red-text"
                                  : ""
                              }
                            >
                              {percent(m.readiness)}
                            </td>
                            <td>
                              {baseline.earliest_constraint
                                ? dateLabel(baseline.earliest_constraint)
                                : "Clear"}{" "}
                              →{" "}
                              {m.earliest_constraint
                                ? dateLabel(m.earliest_constraint)
                                : "Clear"}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </section>
          <section className="panel saved-panel">
            <div className="panel-heading">
              <h2>Saved scenarios</h2>
              <span className="muted">Current dataset</span>
            </div>
            {saved.filter((s) => s.dataset_id === data.dataset_id).length ? (
              saved
                .filter((s) => s.dataset_id === data.dataset_id)
                .map((s) => (
                  <button
                    key={s.id}
                    className="saved-scenario"
                    onClick={() => {
                      void request<Portfolio>(`/scenarios/${s.id}`)
                        .then(setResult)
                        .catch((e) => setError(e.message));
                    }}
                  >
                    <FlaskConical size={16} />
                    <span>{s.name}</span>
                    <span className="muted">Load comparison</span>
                  </button>
                ))
            ) : (
              <Empty>No scenarios saved yet.</Empty>
            )}
          </section>
        </div>
      </div>
    </>
  );
}

export function TransferView({ data }: { data: Portfolio }) {
  const [transit, setTransit] = useState(3);
  const [reserve, setReserve] = useState(1);
  const [sameRegion, setSameRegion] = useState(false);
  const [minimum, setMinimum] = useState(100);
  const [maximum, setMaximum] = useState(100000);
  const [items, setItems] = useState<Transfer[]>([]);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<Transfer | null>(null);
  const run = useCallback(
    async (initial = false) => {
      setBusy(true);
      setError("");
      try {
        setItems(
          await request<Transfer[]>("/transfers", {
            guardrails: initial
              ? {}
              : {
                  transit_days: transit,
                  reserve_multiplier: reserve,
                  same_region_only: sameRegion,
                  min_donor_readiness: minimum,
                  max_transfer: maximum,
                },
          }),
        );
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setBusy(false);
      }
    },
    [transit, reserve, sameRegion, minimum, maximum],
  );
  useEffect(() => {
    void request<Transfer[]>("/transfers", { guardrails: {} })
      .then(setItems)
      .catch((e) => setError(e.message))
      .finally(() => setBusy(false));
  }, []);
  const marketName = (id: string) =>
    data.markets.find((m) => m.market_id === id)?.name || id;
  return (
    <>
      <Heading
        eyebrow="MATERIAL MOVEMENT / RECOMMENDATIONS"
        title="Transfer planner"
        description="Rebalance available stock while preserving each donor’s protected inventory."
      />
      <div className="advisory">
        <ShieldCheck size={19} />
        <span>
          Recommendations only. Every transfer must arrive by the need date and
          preserve donor safety stock across the full 90-day horizon.
        </span>
      </div>
      <section className="panel guardrails">
        <div className="panel-heading">
          <h2>Transfer guardrails</h2>
          <Label>CONFIGURABLE</Label>
        </div>
        <div className="guardrail-inputs">
          <label>
            Transit time (days)
            <input
              type="number"
              min="1"
              max="30"
              value={transit}
              onChange={(e) => setTransit(Number(e.target.value))}
            />
          </label>
          <label>
            Safety stock multiplier
            <input
              type="number"
              min="0"
              max="10"
              step="0.5"
              value={reserve}
              onChange={(e) => setReserve(Number(e.target.value))}
            />
          </label>
          <label>
            Minimum donor score
            <input
              type="number"
              min="0"
              max="100"
              value={minimum}
              onChange={(e) => setMinimum(Number(e.target.value))}
            />
          </label>
          <label>
            Max units per transfer
            <input
              type="number"
              min="1"
              max="1000000"
              value={maximum}
              onChange={(e) => setMaximum(Number(e.target.value))}
            />
          </label>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={sameRegion}
              onChange={(e) => setSameRegion(e.target.checked)}
            />{" "}
            Same region only
          </label>
          <button
            className="primary"
            disabled={busy}
            onClick={() => void run()}
          >
            {busy ? "Calculating…" : "Recalculate"}
          </button>
        </div>
      </section>
      {error && <ErrorMessage message={error} />}
      <section className="panel">
        <div className="panel-heading">
          <h2>
            Feasible transfers{" "}
            <span className="count-chip">{items.length}</span>
          </h2>
          <Label tone="teal">GUARDRAILS APPLIED</Label>
        </div>
        {busy ? (
          <Loading />
        ) : items.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Movement</th>
                  <th>Material</th>
                  <th>Quantity</th>
                  <th>Arrives / needed</th>
                  <th>Donor floor after</th>
                  <th>Evidence</th>
                </tr>
              </thead>
              <tbody>
                {items.map((t) => (
                  <tr key={t.id}>
                    <td>
                      <strong>{marketName(t.from_market)}</strong>
                      <small>to {marketName(t.to_market)}</small>
                    </td>
                    <td>{materialNames[t.material_id] || t.material_id}</td>
                    <td className="teal-text numeric">
                      {t.quantity.toLocaleString()}{" "}
                      {materialUnits[t.material_id] || "units"}
                    </td>
                    <td>
                      {dateLabel(t.arrival_date)}
                      <small>Needed {dateLabel(t.need_date)}</small>
                    </td>
                    <td>
                      {t.donor_min_balance_after.toLocaleString()}
                      <small>
                        Safety floor {t.safety_stock.toLocaleString()}
                      </small>
                    </td>
                    <td>
                      <button
                        className="text-button"
                        onClick={() => setSelected(t)}
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty>
            No safe transfers meet these guardrails. Try a shorter transit time
            or review incoming supply.
          </Empty>
        )}
      </section>
      {selected && (
        <Modal title="Transfer evidence" close={() => setSelected(null)}>
          <div className="advisory">
            <ArrowLeftRight size={22} />
            {marketName(selected.from_market)} to{" "}
            {marketName(selected.to_market)} ·{" "}
            {selected.quantity.toLocaleString()}{" "}
            {materialUnits[selected.material_id]}
          </div>
          <p>
            The donor’s lowest projected balance after this and earlier
            recommendations is{" "}
            {selected.donor_min_balance_after.toLocaleString()}, above the
            safety floor of {selected.safety_stock.toLocaleString()}.
          </p>
          <p>
            Dispatch uses current available inventory. Arrival{" "}
            {dateLabel(selected.arrival_date)} precedes the requirement on{" "}
            {dateLabel(selected.need_date)}.
          </p>
          <h3>Supporting source IDs</h3>
          <div className="source-tags">
            {selected.source_ids.map((id) => (
              <code key={id}>{id}</code>
            ))}
          </div>
        </Modal>
      )}
    </>
  );
}

export function BriefView() {
  const [brief, setBrief] = useState<Brief | null>(null);
  const [period, setPeriod] = useState("weekly");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function run() {
    setBusy(true);
    setError("");
    try {
      setBrief(await request<Brief>("/briefs", { period }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Heading
        eyebrow="EVIDENCE TO ACTION / OPERATIONS BRIEF"
        title="Readiness brief"
        description="A concise briefing whose every statement points back to calculated evidence."
      />
      <section className="panel brief-controls">
        <label>
          Briefing format
          <select value={period} onChange={(e) => setPeriod(e.target.value)}>
            <option value="weekly">Weekly planning brief</option>
            <option value="daily">Daily exception brief</option>
          </select>
        </label>
        <button className="primary" disabled={busy} onClick={() => void run()}>
          <FileText size={16} />
          {busy ? "Preparing brief…" : "Generate brief"}
        </button>
        {brief && (
          <button
            className="secondary"
            onClick={() =>
              saveFile(
                "readiness-brief.md",
                `# ${brief.headline}\n\nMode: ${brief.mode}\n\n${brief.statements.map((s) => `- ${s.text}\n  Evidence: ${s.source_ids.join(", ")}`).join("\n\n")}`,
              )
            }
          >
            <ArrowDownToLine size={16} />
            Export brief
          </button>
        )}
      </section>
      {error && <ErrorMessage message={error} />}
      <section className="panel brief-paper">
        {busy ? (
          <Loading />
        ) : !brief ? (
          <Empty>
            <FileText size={32} />
            <h3>A grounded view of the week ahead</h3>
            <p>
              Works immediately in deterministic mode. Configure Ollama to let a
              local model select and order verified statements.
            </p>
          </Empty>
        ) : (
          <>
            <div className="brief-meta">
              <Label tone={brief.mode === "local-llm" ? "purple" : "teal"}>
                {brief.mode === "local-llm"
                  ? "AI-SELECTED · VERIFIED FACTS"
                  : `${brief.mode.toUpperCase()} NARRATIVE`}
              </Label>
              <span>{brief.period.toUpperCase()} READINESS BRIEF</span>
            </div>
            <h2 className="brief-title">{brief.headline}</h2>
            <p className="muted">
              {brief.mode === "fallback"
                ? "The local model was unavailable or returned invalid evidence. This brief uses the deterministic fallback."
                : "Numbers and dates come directly from the planning engine. Supporting records are linked below each statement."}
            </p>
            <div className="brief-statements">
              {brief.statements.map((s, i) => (
                <article key={s.id}>
                  <span className="statement-index">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <div>
                    <p>{s.text}</p>
                    <details>
                      <summary>
                        Supporting evidence · {s.source_ids.length} source IDs
                      </summary>
                      <div className="source-tags">
                        {s.source_ids.map((id) => (
                          <code key={id}>{id}</code>
                        ))}
                      </div>
                    </details>
                  </div>
                </article>
              ))}
            </div>
            {!brief.statements.length && (
              <Empty>
                No claims generated: required evidence is unavailable.
              </Empty>
            )}
            <details className="telemetry">
              <summary>Observable model telemetry</summary>
              <pre>{JSON.stringify(brief.telemetry, null, 2)}</pre>
            </details>
          </>
        )}
      </section>
    </>
  );
}

export function DataView({ onImport }: { onImport: () => Promise<void> }) {
  const [table, setTable] = useState("purchase_orders");
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<Page | null>(null);
  const [reports, setReports] = useState<Validation[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [row, setRow] = useState<RawRow | null>(null);
  const load = useCallback(async () => {
    setError("");
    setBusy(true);
    try {
      const [p, r] = await Promise.all([
        request<Page>(`/records/${table}?offset=${offset}&limit=20`),
        request<Validation[]>("/validation-reports"),
      ]);
      setPage(p);
      setReports(r);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }, [table, offset]);
  useEffect(() => {
    void load();
  }, [load]);
  async function upload(file: File | undefined) {
    if (!file) return;
    setError("");
    if (
      !file.name.endsWith(".json") ||
      file.size > 20 * 1024 * 1024 ||
      (file.type && !["application/json", "text/plain"].includes(file.type))
    ) {
      setError("Choose a JSON dataset smaller than 20 MiB.");
      return;
    }
    setBusy(true);
    try {
      const raw: unknown = JSON.parse(await file.text());
      const report = await request<Validation>("/imports", raw, true);
      await load();
      if (report.accepted) await onImport();
      else
        setError(
          "Import rejected. The active dataset is unchanged; inspect the validation report below.",
        );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const columns = page?.items.length
    ? Object.keys(page.items[0])
        .filter(
          (k) =>
            ![
              "ingested_at",
              "lineage",
              "validation_status",
              "source_id",
            ].includes(k),
        )
        .slice(0, 7)
    : [];
  return (
    <>
      <Heading
        eyebrow="DATA QUALITY / TRACEABILITY"
        title="Data & provenance"
        description="Inspect source records, their lineage, and every import validation result."
      />
      <div className="advisory">
        <Database size={20} />
        <span>
          Imports replace the active snapshot only after all records pass
          validation. Every failed row stays visible in its report.
        </span>
      </div>
      {error && <ErrorMessage message={error} />}
      <section className="panel">
        <div className="panel-heading">
          <div className="filters">
            <select
              aria-label="Dataset table"
              value={table}
              onChange={(e) => {
                setTable(e.target.value);
                setOffset(0);
              }}
            >
              {[
                "markets",
                "materials",
                "boms",
                "plans",
                "inventory",
                "purchase_orders",
                "commitments",
                "consumption",
              ].map((t) => (
                <option key={t} value={t}>
                  {t.replaceAll("_", " ")}
                </option>
              ))}
            </select>
            <Label>RAW RECORDS</Label>
            <span className="muted">
              {page?.total.toLocaleString()} records
            </span>
          </div>
          <label className="secondary upload-button">
            <Upload size={16} /> Import dataset
            <input
              type="file"
              accept="application/json,.json"
              aria-label="Import JSON dataset"
              onChange={(e) => {
                void upload(e.target.files?.[0]);
                e.target.value = "";
              }}
            />
          </label>
        </div>
        {busy ? (
          <Loading />
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  {columns.map((c) => (
                    <th key={c}>{c.replaceAll("_", " ")}</th>
                  ))}
                  <th>Provenance</th>
                </tr>
              </thead>
              <tbody>
                {page?.items.map((r, i) => (
                  <tr key={String(r.id || i)}>
                    {columns.map((c) => (
                      <td key={c}>
                        {typeof r[c] === "object"
                          ? JSON.stringify(r[c])
                          : String(r[c] ?? "—")}
                      </td>
                    ))}
                    <td>
                      <button className="text-button" onClick={() => setRow(r)}>
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="table-footer">
          <span>
            Rows {page?.total ? offset + 1 : 0}–
            {Math.min(offset + 20, page?.total || 0)} of {page?.total || 0}
          </span>
          <div className="filters">
            <button
              className="secondary small"
              disabled={!offset || busy}
              onClick={() => setOffset(Math.max(0, offset - 20))}
            >
              Previous
            </button>
            <button
              className="secondary small"
              disabled={offset + 20 >= (page?.total || 0) || busy}
              onClick={() => setOffset(offset + 20)}
            >
              Next
            </button>
          </div>
        </div>
      </section>
      <section className="panel validation-panel">
        <div className="panel-heading">
          <h2>Validation reports</h2>
          <Label>AUDIT TRAIL</Label>
        </div>
        {reports.map((r) => (
          <details key={r.id} className="validation-report" open={!r.accepted}>
            <summary>
              <Label tone={r.accepted ? "teal" : "red"}>
                {r.accepted ? "Accepted" : "Rejected"}
              </Label>
              <strong>{r.dataset_id}</strong>
              <span>
                {r.checked_records.toLocaleString()} records · {r.issues.length}{" "}
                findings
              </span>
            </summary>
            {r.issues.length ? (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Severity</th>
                      <th>Record</th>
                      <th>Finding</th>
                    </tr>
                  </thead>
                  <tbody>
                    {r.issues.map((x, i) => (
                      <tr key={i}>
                        <td
                          className={
                            x.severity === "error" ? "red-text" : "amber-text"
                          }
                        >
                          {x.severity}
                        </td>
                        <td>{x.record_id}</td>
                        <td>{x.message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="teal-text">All validation checks passed.</p>
            )}
          </details>
        ))}
      </section>
      {row && (
        <Modal title="Source record & lineage" close={() => setRow(null)}>
          <Label>RAW DATA</Label>
          <pre className="raw-json">{JSON.stringify(row, null, 2)}</pre>
        </Modal>
      )}
    </>
  );
}

export function ForecastView({ data }: { data: Portfolio }) {
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [market, setMarket] = useState(data.markets[0].market_id);
  const [material, setMaterial] = useState(
    data.requirements.some((r) => r.material_id === "fiber")
      ? "fiber"
      : data.requirements[0]?.material_id || "",
  );
  const [error, setError] = useState("");
  useEffect(() => {
    void request<Forecast>("/forecast")
      .then(setForecast)
      .catch((e) => setError(e.message));
  }, []);
  const series = forecast?.series.find(
    (s) => s.market_id === market && s.material_id === material,
  );
  const chart = {
    ...chartTheme,
    xAxis: {
      ...chartTheme.xAxis,
      data: series?.prediction?.map((p) => dateLabel(p.date)),
    },
    series: [
      {
        name: "Weekday-mean forecast",
        type: "line",
        data: series?.prediction?.map((p) => p.quantity),
        lineStyle: { color: "#aa9bf5", width: 3, type: "dashed" },
        itemStyle: { color: "#aa9bf5" },
        symbolSize: 7,
      },
    ],
  };
  return (
    <>
      <Heading
        eyebrow="STATISTICAL MODEL / CONSUMPTION"
        title="Demand forecast"
        description="An interpretable weekday-mean model, measured against held-out consumption."
      />
      <div className="advisory">
        <ShieldCheck size={19} />
        <span>
          Forecasts are diagnostic. Scheduled BOM demand drives readiness;
          historical usage is already reflected in inventory.
        </span>
      </div>
      {error && <ErrorMessage message={error} />}
      <section className="panel">
        <div className="panel-heading">
          <div className="filters">
            <select
              aria-label="Forecast market"
              value={market}
              onChange={(e) => setMarket(e.target.value)}
            >
              {data.markets.map((m) => (
                <option key={m.market_id} value={m.market_id}>
                  {m.name}
                </option>
              ))}
            </select>
            <select
              aria-label="Forecast material"
              value={material}
              onChange={(e) => setMaterial(e.target.value)}
            >
              {[...new Set(data.requirements.map((r) => r.material_id))].map(
                (id) => (
                  <option key={id} value={id}>
                    {materialNames[id] || id}
                  </option>
                ),
              )}
            </select>
          </div>
          <Label tone="purple">MODEL PREDICTION</Label>
        </div>
        {!forecast ? (
          <Loading />
        ) : !series?.prediction ? (
          <Empty>
            Insufficient consumption evidence for this market and material.
          </Empty>
        ) : (
          <>
            <div className="forecast-metrics">
              <div>
                <span>Backtest MAE</span>
                <strong>
                  {series.mae?.toFixed(2)}{" "}
                  <small>{materialUnits[material] || "units"}/day</small>
                </strong>
              </div>
              <div>
                <span>Backtest WAPE</span>
                <strong>
                  {series.wape == null ? "N/A" : percent(series.wape * 100)}
                </strong>
              </div>
              <div>
                <span>Observations</span>
                <strong>
                  {series.training_observations}
                  <small> days</small>
                </strong>
              </div>
              <div>
                <span>Forecast horizon</span>
                <strong>
                  14<small> days</small>
                </strong>
              </div>
            </div>
            <Chart
              option={chart}
              height={340}
              label={`Fourteen-day consumption forecast for ${materialNames[material] || material}`}
            />
            <div className="chart-caption">
              Dashed line = statistical prediction · 14 observations held out
              for evaluation · {forecast.model}
            </div>
            <details className="telemetry">
              <summary>View exact predicted quantities</summary>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Predicted units</th>
                    </tr>
                  </thead>
                  <tbody>
                    {series.prediction.map((p) => (
                      <tr key={p.date}>
                        <td>{p.date}</td>
                        <td>{p.quantity}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          </>
        )}
      </section>
    </>
  );
}

export function AboutView() {
  return (
    <>
      <Heading
        eyebrow="SYSTEM DESIGN / OPEN SOURCE"
        title="Built on evidence"
        description="Deterministic planning at the center. Local AI at the narrative boundary."
      />
      <section className="panel about-intro">
        <Label tone="teal">APACHE-2.0</Label>
        <h2>Healthy inventory does not guarantee a ready market.</h2>
        <p>
          Material must be available in the correct market before its build
          phase begins. MarketReadiness combines BOM requirements, available
          stock, purchase orders, supplier commitments, and phase dependencies
          to expose those timing gaps.
        </p>
        <div className="architecture-flow">
          {[
            ["01", "Source snapshots", "Plans · BOM · inventory · POs"],
            ["02", "Validated ledger", "Atomic import · provenance"],
            ["03", "Planning engine", "Allocation · critical path · transfers"],
            ["04", "Evidence workspace", "API · scenarios · local briefs"],
          ].map(([n, t, d]) => (
            <div key={n}>
              <span>{n}</span>
              <h3>{t}</h3>
              <p>{d}</p>
            </div>
          ))}
        </div>
      </section>
      <div className="about-grid">
        <section className="panel">
          <h2>What the score means</h2>
          <p>
            A requirement’s readiness is its on-time coverage divided by its BOM
            quantity. The lowest material score sets a phase and market’s
            readiness. Portfolio readiness weights market scores by planned
            homes.
          </p>
          <p>
            Confirmed supply is allocated in need-date order. Delays propagate
            through predecessor phases; unresolved supply yields an unresolved
            completion date.
          </p>
          <Label>DETERMINISTIC</Label>
        </section>
        <section className="panel">
          <h2>What the model can do</h2>
          <p>
            With Ollama enabled, a local model selects and orders existing
            evidence IDs. The application renders their exact facts. Unknown
            IDs, conflicting posture, malformed output, and model failures
            trigger a safe fallback.
          </p>
          <p>
            No model writes inventory, calculates a KPI, executes SQL, or runs a
            shell command.
          </p>
          <Label tone="purple">OPTIONAL LOCAL AI</Label>
        </section>
        <section className="panel">
          <h2>Reproducible by default</h2>
          <ul className="check-list">
            <li>
              <Check size={16} /> Seeded synthetic portfolio across 14 markets
            </li>
            <li>
              <Check size={16} /> Fixed planning date: September 28, 2026
            </li>
            <li>
              <Check size={16} /> No paid API keys or cloud dependencies
            </li>
            <li>
              <Check size={16} /> PostgreSQL + FastAPI + React + ECharts
            </li>
          </ul>
        </section>
        <section className="panel">
          <h2>Practical boundaries</h2>
          <p>
            This is a single-program planning demonstrator. BOM quantities are
            reserved at phase start; it does not schedule daily installation
            crews. Transfers are advisory and use a configurable fixed transit
            time.
          </p>
          <p>
            Readiness is a coverage measure, not a calibrated probability. No
            live ERP integration or enterprise certification is claimed.
          </p>
        </section>
      </div>
    </>
  );
}
