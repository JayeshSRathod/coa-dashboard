export type WorkspaceId = "trader" | "portfolio" | "research" | "operations";
export type StatusTone = "positive" | "warning" | "negative" | "neutral";
export interface Kpi { label: string; value: string; detail: string; tone: StatusTone }
export interface TableRow { [column: string]: string | number }
export interface Panel { id: string; title: string; subtitle: string; kind: "table" | "chart" | "timeline" | "status"; columns?: string[]; rows?: TableRow[]; message?: string }
export interface WorkspaceDefinition { id: WorkspaceId; label: string; description: string; kpis: Kpi[]; panels: Panel[] }

const table = (id: string, title: string, subtitle: string, columns: string[]): Panel => ({ id, title, subtitle, kind: "table", columns, rows: [] });
const message = (id: string, title: string, subtitle: string, kind: "chart" | "timeline" | "status", text: string): Panel => ({ id, title, subtitle, kind, message: text });

export const workspaces: Record<WorkspaceId, WorkspaceDefinition> = {
  trader: { id: "trader", label: "Trader", description: "Single-screen market monitoring, opportunities, positions, and alerts.", kpis: [
    { label: "Execution", value: "PAPER", detail: "Live orders disabled", tone: "neutral" }, { label: "Signals", value: "0", detail: "No eligible signals", tone: "neutral" }, { label: "Open positions", value: "0", detail: "No paper positions", tone: "neutral" }, { label: "Risk", value: "0.0%", detail: "Of configured capital", tone: "positive" },
  ], panels: [
    table("scanner", "Ranked Scanner", "Opportunity queue", ["Rank", "Symbol", "Score", "Signal", "Trend", "Age"]),
    message("chart", "Market Context", "Select a symbol from the scanner or watchlist", "chart", "No market stream is connected. The future workstation API will provide read-only chart data."),
    table("watchlist", "Watchlist", "Tracked instruments", ["Symbol", "Last", "Change", "Status"]),
    table("positions", "Positions", "Paper positions only", ["Instrument", "Qty", "Entry", "P&L", "Risk"]),
    message("alerts", "Alerts", "Operational and market notifications", "timeline", "No active alerts."),
  ] },
  portfolio: { id: "portfolio", label: "Portfolio", description: "Capital, exposure, Greeks, drawdown, and performance in one workspace.", kpis: [
    { label: "Capital", value: "₹0", detail: "No portfolio selected", tone: "neutral" }, { label: "Exposure", value: "₹0", detail: "No open exposure", tone: "positive" }, { label: "Portfolio delta", value: "0.00", detail: "No options positions", tone: "neutral" }, { label: "Drawdown", value: "0.0%", detail: "No completed trades", tone: "positive" },
  ], panels: [
    message("equity", "Equity & Drawdown", "Historical portfolio performance", "chart", "No performance snapshots are available."),
    table("exposure", "Exposure", "Instrument and expiry allocation", ["Instrument", "Expiry", "Invested", "Risk", "Delta"]),
    table("greeks", "Portfolio Greeks", "Aggregated option sensitivities", ["Delta", "Gamma", "Theta", "Vega"]),
    message("performance", "Performance", "Completed paper-trade metrics", "status", "No completed paper trades are available for analysis."),
  ] },
  research: { id: "research", label: "Research", description: "Strategies, experiments, deterministic evidence, and comparisons.", kpis: [
    { label: "Strategies", value: "0", detail: "No strategy registered", tone: "neutral" }, { label: "Experiments", value: "0", detail: "No completed runs", tone: "neutral" }, { label: "Datasets", value: "0", detail: "No registered datasets", tone: "neutral" }, { label: "Knowledge facts", value: "0", detail: "No derived evidence", tone: "neutral" },
  ], panels: [
    table("strategies", "Strategy Lab", "Immutable strategy versions", ["Strategy", "Version", "Status", "Market"]),
    table("experiments", "Experiments", "Controlled deterministic research", ["Experiment", "Strategy", "Dataset", "Status"]),
    message("knowledge", "Research Knowledge", "Evidence-linked summaries", "timeline", "No research facts are available."),
    message("comparison", "Comparison", "Strategy and experiment evidence", "status", "Select completed experiments to compare when data is available."),
  ] },
  operations: { id: "operations", label: "Operations", description: "Health, broker state, data freshness, scheduler activity, and audit evidence.", kpis: [
    { label: "System health", value: "UNKNOWN", detail: "No EOC observations", tone: "warning" }, { label: "Broker", value: "DISABLED", detail: "Live execution unavailable", tone: "neutral" }, { label: "Data feed", value: "OFFLINE", detail: "No market provider configured", tone: "warning" }, { label: "Alerts", value: "0", detail: "No active alerts", tone: "positive" },
  ], panels: [
    table("health", "System Health", "Enterprise Operations Center", ["Component", "Status", "Updated", "Details"]),
    message("broker", "Broker & Execution", "Safety-first connection state", "status", "Execution is restricted to DISABLED or PAPER. Configure credentials in Dashboard 2.0 until the workstation configuration API is introduced."),
    table("scheduler", "Scheduler", "Job observations", ["Job", "Status", "Last run", "Next run"]),
    message("audit", "Audit Timeline", "Immutable operational evidence", "timeline", "No audit events are available."),
  ] },
};

export const workspaceOrder: WorkspaceId[] = ["trader", "portfolio", "research", "operations"];
