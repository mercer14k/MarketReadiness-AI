import { Label, ErrorMessage, Empty, Loading, Modal } from "./components";
import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  ArrowDownToLine,
  ArrowLeftRight,
  BookOpen,
  Boxes,
  ChevronRight,
  CircleHelp,
  Database,
  FileText,
  FlaskConical,
  LayoutDashboard,
  Menu,
  RefreshCw,
  Search,
  ShieldCheck,
  TrendingUp,
  X,
} from "lucide-react";
import {
  dateLabel,
  exportCSV,
  materialNames,
  percent,
  request,
  setToken,
} from "./api";
import { Chart, chartTheme } from "./Chart";
import type { Market, Portfolio, Requirement } from "./types";
import {
  ScenarioView,
  TransferView,
  BriefView,
  DataView,
  ForecastView,
  AboutView,
} from "./Views";

const pages = [
  { id: "portfolio", name: "Portfolio overview", icon: LayoutDashboard },
  { id: "scenarios", name: "Scenario lab", icon: FlaskConical },
  { id: "transfers", name: "Transfer planner", icon: ArrowLeftRight },
  { id: "forecast", name: "Demand forecast", icon: TrendingUp },
  { id: "brief", name: "Readiness brief", icon: FileText },
  { id: "data", name: "Data & provenance", icon: Database },
  { id: "about", name: "Architecture", icon: BookOpen },
];
export default function App() {
  const [page, setPage] = useState("portfolio");
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);
  const [mobile, setMobile] = useState(false);
  const [market, setMarket] = useState<Market | null>(null);
  const [credential, setCredential] = useState("");
  const load = useCallback(async () => {
    setBusy(true);
    setError("");
    try {
      setPortfolio(await request<Portfolio>("/portfolio"));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }, []);
  useEffect(() => {
    void load();
  }, [load]);
  const navigate = (id: string) => {
    setPage(id);
    setMobile(false);
    window.scrollTo(0, 0);
  };
  return (
    <div className="app">
      <a className="skip" href="#main">
        Skip to main content
      </a>
      <aside className={`sidebar ${mobile ? "open" : ""}`}>
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            navigate("portfolio");
          }}
        >
          <span className="brand-icon">
            <Activity size={24} />
          </span>
          <span>
            MarketReadiness
            <span className="brand-sub">DEPLOYMENT INTELLIGENCE</span>
          </span>
        </a>
        <div className="workspace-label">
          WORKSPACE <span>01</span>
        </div>
        <nav aria-label="Primary">
          {pages.map((p, i) => (
            <button
              key={p.id}
              className={`${page === p.id ? "active" : ""} ${i === 5 ? "nav-divider" : ""}`}
              onClick={() => navigate(p.id)}
              aria-current={page === p.id ? "page" : undefined}
            >
              <p.icon size={18} />
              {p.name}
              {p.id === "portfolio" && portfolio && (
                <span className="nav-count">{portfolio.markets.length}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="local-status">
            <ShieldCheck size={18} />
            <div>
              Local by design<small>No cloud AI required</small>
            </div>
          </div>
          <div className="profile">
            <span className="avatar">MR</span>
            <div>
              Infrastructure program<small>Synthetic demo · v0.1.0</small>
            </div>
          </div>
        </div>
      </aside>
      <div className="shell">
        <header className="topbar">
          <div className="crumb">
            <button
              className="icon-button menu-toggle"
              aria-label="Toggle navigation"
              onClick={() => setMobile(!mobile)}
            >
              <Menu size={20} />
            </button>
            <span>Workspace</span>
            <ChevronRight size={14} />
            <strong>{pages.find((p) => p.id === page)?.name}</strong>
          </div>
          <div className="topbar-right">
            <Label>SYNTHETIC DATA</Label>
            <span className="as-of">
              As of {portfolio ? dateLabel(portfolio.as_of) : "—"},{" "}
              {portfolio?.as_of.slice(0, 4)}
            </span>
            <button
              className="icon-button"
              aria-label="Refresh data"
              onClick={() => void load()}
            >
              <RefreshCw size={16} />
            </button>
          </div>
        </header>
        <main id="main" tabIndex={-1}>
          {error && (
            <>
              <ErrorMessage message={error} />
              <form
                className="auth-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  setToken(credential);
                  void load();
                }}
              >
                <label>
                  For secured mode, enter your API token
                  <input
                    type="password"
                    value={credential}
                    onChange={(e) => setCredential(e.target.value)}
                    autoComplete="off"
                  />
                </label>
                <button className="primary">Connect</button>
                <button
                  type="button"
                  className="secondary"
                  onClick={() => void load()}
                >
                  Retry
                </button>
              </form>
            </>
          )}
          {busy && !portfolio ? (
            <Loading />
          ) : (
            portfolio && (
              <>
                {page === "portfolio" && (
                  <PortfolioView
                    data={portfolio}
                    onMarket={setMarket}
                    onNavigate={navigate}
                  />
                )}
                {page === "scenarios" && <ScenarioView data={portfolio} />}
                {page === "transfers" && <TransferView data={portfolio} />}
                {page === "forecast" && <ForecastView data={portfolio} />}
                {page === "brief" && <BriefView />}
                {page === "data" && <DataView onImport={load} />}
                {page === "about" && <AboutView />}
                <footer>
                  <span>
                    <ShieldCheck size={14} /> Calculated from source evidence ·{" "}
                    {portfolio.algorithm_version}
                  </span>
                  <span>{portfolio.dataset_id}</span>
                </footer>
              </>
            )
          )}
        </main>
      </div>
      {market && portfolio && (
        <MarketDetail
          market={market}
          data={portfolio}
          close={() => setMarket(null)}
        />
      )}
    </div>
  );
}

function PortfolioView({
  data,
  onMarket,
  onNavigate,
}: {
  data: Portfolio;
  onMarket: (m: Market) => void;
  onNavigate: (id: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("All markets");
  const [error, setError] = useState("");
  const atRisk = data.markets.filter((m) => m.status !== "Ready");
  const homes = data.markets.reduce((n, m) => n + m.homes, 0);
  const blockers = data.requirements.filter((r) => r.shortage > 0);
  const earliest = atRisk
    .map((m) => m.earliest_constraint)
    .filter((v): v is string => !!v)
    .sort()[0];
  const visible = data.markets.filter(
    (m) =>
      m.name.toLowerCase().includes(query.toLowerCase()) &&
      (status === "All markets" || m.status === status),
  );
  const families = ["Civil", "Fiber", "Connectivity", "Electronics"];
  const chart = {
    ...chartTheme,
    xAxis: {
      ...chartTheme.xAxis,
      data: data.timeline.map((t) => dateLabel(t.date)),
    },
    yAxis: {
      ...chartTheme.yAxis,
      name: "Homes",
      nameTextStyle: { color: "#94a3b8" },
    },
    series: [
      {
        name: "Material-constrained schedule",
        type: "line",
        smooth: false,
        step: "end",
        data: data.timeline.map((t) => t.cumulative_homes),
        symbolSize: 6,
        lineStyle: { color: "#4fd1b5", width: 3 },
        itemStyle: { color: "#4fd1b5" },
        areaStyle: { color: "rgba(79,209,181,.09)" },
      },
    ],
  };
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">PROGRAM CONTROL / 90-DAY OUTLOOK</div>
          <h1>
            Deployment readiness<span className="heading-dot">.</span>
          </h1>
          <p>
            Surface material constraints before they become construction delays.
          </p>
        </div>
        <div className="heading-actions">
          <button
            className="secondary"
            onClick={() => {
              void exportCSV().catch((e) => setError(e.message));
            }}
          >
            <ArrowDownToLine size={16} /> Export
          </button>
          <button className="primary" onClick={() => onNavigate("scenarios")}>
            <FlaskConical size={16} /> Run a scenario
          </button>
        </div>
      </div>
      {error && <ErrorMessage message={error} />}
      <section className="metrics" aria-label="Portfolio metrics">
        <div className="metric featured">
          <div className="metric-title">
            Portfolio readiness <Label tone="teal">COMPUTED</Label>
          </div>
          <div className="metric-value">
            {percent(data.readiness)}
            <Activity size={27} />
          </div>
          <div className="meter">
            <span style={{ width: `${data.readiness}%` }} />
          </div>
          <small>Homes-weighted market bottleneck score</small>
        </div>
        <div className="metric">
          <div className="metric-title">
            Markets ready <Boxes size={17} />
          </div>
          <div className="metric-value">
            {data.markets.length - atRisk.length}
            <span>/ {data.markets.length}</span>
          </div>
          <small>
            <b className="teal-text">{homes.toLocaleString()}</b> homes in the
            build program
          </small>
        </div>
        <div className="metric">
          <div className="metric-title">
            Material blockers <span className="risk-dot" />
          </div>
          <div className="metric-value amber-text">
            {blockers.length.toString().padStart(2, "0")}
          </div>
          <small>Across {atRisk.length} markets requiring attention</small>
        </div>
        <div className="metric">
          <div className="metric-title">
            First constraint <span className="small-icon">↳</span>
          </div>
          <div className="metric-value date-value">
            {earliest ? dateLabel(earliest) : "None"}
          </div>
          <small>
            {earliest
              ? "Earliest impacted phase start"
              : "No constraints in this horizon"}
          </small>
        </div>
      </section>
      {atRisk.length > 0 && (
        <div className="attention-strip">
          <span className="attention-icon">!</span>
          <div>
            <strong>{atRisk.length} markets need a closer look.</strong>
            <span>
              {" "}
              Confirmed supply does not cover every planned phase on time.
            </span>
          </div>
          <button
            onClick={() => {
              setStatus("At risk");
              document
                .getElementById("market-table")
                ?.scrollIntoView({ behavior: "smooth", block: "start" });
            }}
          >
            Review constraints <ChevronRight size={16} />
          </button>
        </div>
      )}
      <div className="analytics-grid">
        <section className="panel timeline-panel">
          <div className="panel-heading">
            <div>
              <h2>Readiness timeline</h2>
              <p>Homes reaching activation under material constraints</p>
            </div>
            <Label>PROJECTED · DETERMINISTIC</Label>
          </div>
          <Chart
            option={chart}
            label="Projected cumulative homes reaching activation, based on material supply and phase dependencies"
          />
          <div className="chart-caption">
            <span className="legend-line" /> Earliest feasible activation{" "}
            <span>Unresolved phases excluded</span>
          </div>
        </section>
        <section className="panel exposure-panel">
          <div className="panel-heading">
            <div>
              <h2>Material exposure</h2>
              <p>Markets below full readiness by family</p>
            </div>
            <Boxes size={18} />
          </div>
          <div className="exposure-list">
            {families.map((f) => {
              const count = data.markets.filter(
                (m) => (m.families[f] ?? 100) < 100,
              ).length;
              return (
                <div className="exposure" key={f}>
                  <div>
                    <span>{f}</span>
                    <strong>
                      {count}
                      <small> / {data.markets.length}</small>
                    </strong>
                  </div>
                  <div className="segment-bar">
                    {data.markets.map((m, i) => (
                      <span
                        key={m.market_id}
                        className={i < count ? "exposed" : ""}
                      />
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mini-note">
            <CircleHelp size={14} /> A market is only as ready as its limiting
            material.
          </div>
        </section>
      </div>
      <section className="panel market-panel" id="market-table">
        <div className="panel-heading">
          <div className="title-with-count">
            <h2>Market readiness</h2>
            <span className="count-chip">{visible.length}</span>
          </div>
          <div className="filters">
            <label className="search">
              <Search size={16} />
              <input
                aria-label="Search markets"
                placeholder="Search markets…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </label>
            <select
              aria-label="Filter market status"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              {["All markets", "At risk", "Ready", "Watch"].map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Market / region</th>
                <th>Planned homes</th>
                <th>Readiness</th>
                <th>Status</th>
                <th>First constraint</th>
                <th>Blockers</th>
                <th>
                  <span className="sr-only">Details</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {visible.map((m) => (
                <tr key={m.market_id}>
                  <td>
                    <button className="market-link" onClick={() => onMarket(m)}>
                      {m.name}
                    </button>
                    <small>{m.region}</small>
                  </td>
                  <td className="numeric">{m.homes.toLocaleString()}</td>
                  <td>
                    <div className="inline-readiness">
                      <span
                        className={`score ${m.readiness < 80 ? "red-text" : m.readiness < 100 ? "amber-text" : "teal-text"}`}
                      >
                        {percent(m.readiness)}
                      </span>
                      <div className="tiny-meter">
                        <span
                          style={{
                            width: `${m.readiness}%`,
                            background:
                              m.readiness < 80
                                ? "#f58d91"
                                : m.readiness < 100
                                  ? "#e6b45c"
                                  : "#4fd1b5",
                          }}
                        />
                      </div>
                    </div>
                  </td>
                  <td>
                    <Label tone={m.status === "Ready" ? "teal" : "amber"}>
                      {m.status}
                    </Label>
                  </td>
                  <td>
                    {m.earliest_constraint ? (
                      dateLabel(m.earliest_constraint)
                    ) : (
                      <span className="muted">Clear</span>
                    )}
                  </td>
                  <td>
                    {m.blockers ? (
                      <span className="blocker-count">
                        {m.blockers} material{m.blockers > 1 ? "s" : ""}
                      </span>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                  <td>
                    <button
                      className="icon-button"
                      aria-label={`View ${m.name} evidence`}
                      onClick={() => onMarket(m)}
                    >
                      <ChevronRight size={18} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!visible.length && <Empty>No markets match this filter.</Empty>}
        <div className="table-footer">
          Showing {visible.length} of {data.markets.length} markets
          <span>
            Readiness is calculated at material, phase, and market level
          </span>
        </div>
      </section>
      {data.warnings.length > 0 && (
        <details className="planning-warnings">
          <summary>
            Supply assumptions &amp; exclusions · {data.warnings.length}
          </summary>
          <ul>
            {data.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </details>
      )}
    </>
  );
}

function MarketDetail({
  market,
  data,
  close,
}: {
  market: Market;
  data: Portfolio;
  close: () => void;
}) {
  const [evidence, setEvidence] = useState<Requirement | null>(null);
  const phases = data.phases.filter((p) => p.market_id === market.market_id);
  const requirements = data.requirements.filter(
    (r) => r.market_id === market.market_id,
  );
  return (
    <Modal
      title={`${market.name} · ${percent(market.readiness)} ready`}
      close={close}
    >
      <p className="muted">
        {market.region} region · {market.homes.toLocaleString()} homes ·
        computed from {data.dataset_id}
      </p>
      <h3>Build sequence & critical path</h3>
      <div className="phase-sequence">
        {phases.map((p, i) => (
          <div
            className={`phase-card ${p.delay_days !== 0 ? "constrained" : ""}`}
            key={p.plan_id}
          >
            <span className="step">0{i + 1}</span>
            <strong>{p.phase}</strong>
            <div className="phase-dates">
              <span>
                Planned <b>{dateLabel(p.planned_start)}</b>
              </span>
              <span>
                Feasible <b>{dateLabel(p.earliest_start)}</b>
              </span>
            </div>
            <Label tone={p.delay_days === 0 ? "teal" : "amber"}>
              {p.delay_days === null
                ? "Unresolved"
                : p.delay_days
                  ? `${p.delay_days} days late`
                  : "On schedule"}
            </Label>
          </div>
        ))}
      </div>
      <p className="mini-note">
        Binding constraint path: {phases.at(-1)?.critical_path.join(" → ")}.
        Completion is unresolved when confirmed supply is insufficient.
      </p>
      <h3>
        Material requirements <Label>COMPUTED</Label>
      </h3>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Material</th>
              <th>Required</th>
              <th>On time</th>
              <th>Shortfall</th>
              <th>Need date</th>
              <th>Evidence</th>
            </tr>
          </thead>
          <tbody>
            {requirements.map((r) => (
              <tr key={r.id}>
                <td>
                  {materialNames[r.material_id] || r.material_id}
                  <small>{r.family}</small>
                </td>
                <td>{r.quantity.toLocaleString()}</td>
                <td>{r.on_time_quantity.toLocaleString()}</td>
                <td className={r.shortage ? "amber-text" : "muted"}>
                  {r.shortage.toLocaleString()}
                </td>
                <td>{dateLabel(r.due_date)}</td>
                <td>
                  <button
                    className="text-button"
                    onClick={() => setEvidence(r)}
                  >
                    Inspect
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {evidence && (
        <div className="evidence-box">
          <div className="panel-heading">
            <h3>
              {materialNames[evidence.material_id] || evidence.material_id} ·
              supporting records
            </h3>
            <button
              className="icon-button"
              aria-label="Close evidence"
              onClick={() => setEvidence(null)}
            >
              <X size={16} />
            </button>
          </div>
          <p>
            Ready date: {dateLabel(evidence.material_ready_date)}. Requirement{" "}
            {evidence.id}.
          </p>
          <div className="source-tags">
            {evidence.source_ids.map((id) => (
              <code key={id}>{id}</code>
            ))}
          </div>
        </div>
      )}
      <h3>
        Time-phased inventory ledger <Label>COMPUTED</Label>
      </h3>
      <div className="table-scroll ledger-table">
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Material</th>
              <th>Receipts</th>
              <th>Demand</th>
              <th>Projected balance</th>
            </tr>
          </thead>
          <tbody>
            {data.ledger
              .filter((l) => l.market_id === market.market_id)
              .sort((a, b) => a.date.localeCompare(b.date))
              .map((l, i) => (
                <tr key={i}>
                  <td>{dateLabel(l.date)}</td>
                  <td>{materialNames[l.material_id] || l.material_id}</td>
                  <td>+{l.receipts.toLocaleString()}</td>
                  <td>{l.demand.toLocaleString()}</td>
                  <td className={l.balance < 0 ? "red-text" : ""}>
                    {l.balance.toLocaleString()}
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </Modal>
  );
}
