import { useEffect, useState } from "react";
import { type Panel, type WorkspaceId, workspaceOrder, workspaces } from "./workspace";

function StatusDot({ tone }: { tone: "positive" | "warning" | "negative" | "neutral" }) {
  return <span aria-hidden="true" className={`status-dot ${tone}`} />;
}

function PanelCard({ panel }: { panel: Panel }) {
  return <section className={`panel panel-${panel.kind}`} aria-label={panel.title}>
    <header><div><h2>{panel.title}</h2><p>{panel.subtitle}</p></div><button className="panel-action" type="button" aria-label={`Open ${panel.title} detail`}>↗</button></header>
    {panel.kind === "table" ? <div className="empty-table"><div className="table-head">{panel.columns?.map((column) => <span key={column}>{column}</span>)}</div><p>No data is currently available.</p></div> : <div className="empty-panel"><span className="placeholder-icon" aria-hidden="true">{panel.kind === "chart" ? "⌁" : panel.kind === "timeline" ? "◷" : "i"}</span><p>{panel.message}</p></div>}
  </section>;
}

export default function App() {
  const [workspaceId, setWorkspaceId] = useState<WorkspaceId>("trader");
  const [commandOpen, setCommandOpen] = useState(false);
  const [query, setQuery] = useState("");
  const workspace = workspaces[workspaceId];

  useEffect(() => {
    const listener = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") { event.preventDefault(); setCommandOpen(true); }
      if (event.key === "Escape") setCommandOpen(false);
    };
    window.addEventListener("keydown", listener);
    return () => window.removeEventListener("keydown", listener);
  }, []);

  const chooseWorkspace = (id: WorkspaceId) => { setWorkspaceId(id); setCommandOpen(false); setQuery(""); };
  const options = workspaceOrder.filter((id) => workspaces[id].label.toLowerCase().includes(query.toLowerCase()));

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark">CQ</span><span><strong>CQRP</strong><small>WORKSTATION 3.0</small></span></div>
      <nav aria-label="Workspace navigation">
        <p className="nav-label">WORKSPACES</p>
        {workspaceOrder.map((id) => <button key={id} className={workspaceId === id ? "nav-item active" : "nav-item"} onClick={() => chooseWorkspace(id)} type="button"><span aria-hidden="true">{id === "trader" ? "⌁" : id === "portfolio" ? "▦" : id === "research" ? "◌" : "⚙"}</span>{workspaces[id].label}</button>)}
      </nav>
      <div className="sidebar-footer"><StatusDot tone="neutral" /><span>Execution is paper only</span></div>
    </aside>
    <main>
      <header className="topbar"><div><p className="eyebrow">CQRP / {workspace.label.toUpperCase()}</p><h1>{workspace.label} Workspace</h1></div><div className="topbar-actions"><button className="command-button" onClick={() => setCommandOpen(true)} type="button">⌘ <span>Command</span><kbd>Ctrl K</kbd></button><span className="live-status"><StatusDot tone="neutral" /> DATA OFFLINE</span></div></header>
      <section className="workspace-intro"><p>{workspace.description}</p><div className="market-meta"><span>Provider: <b>Unconfigured</b></span><span>Latency: <b>—</b></span><span>Snapshot age: <b>—</b></span><span>Quality: <b>OFFLINE</b></span></div></section>
      <section className="kpi-grid" aria-label="Workspace summary">{workspace.kpis.map((kpi) => <article className="kpi-card" key={kpi.label}><div><p>{kpi.label}</p><strong>{kpi.value}</strong></div><span className={`badge ${kpi.tone}`}><StatusDot tone={kpi.tone} /> {kpi.detail}</span></article>)}</section>
      <section className={`panel-grid ${workspace.id}`}>{workspace.panels.map((panel) => <PanelCard key={panel.id} panel={panel} />)}</section>
    </main>
    {commandOpen && <div className="command-overlay" role="dialog" aria-modal="true" aria-label="Command palette" onMouseDown={() => setCommandOpen(false)}><div className="command-palette" onMouseDown={(event) => event.stopPropagation()}><input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Jump to a workspace…" aria-label="Search workspaces" />{options.map((id) => <button key={id} onClick={() => chooseWorkspace(id)} type="button"><span>{workspaces[id].label}</span><small>{workspaces[id].description}</small></button>)}{!options.length && <p className="no-match">No workspace matches “{query}”.</p>}</div></div>}
  </div>;
}
