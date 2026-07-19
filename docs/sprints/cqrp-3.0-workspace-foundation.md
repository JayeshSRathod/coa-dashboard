# CQRP 3.0 — Workspace Foundation

## Objective

Introduce a professional, panel-based workstation without changing deterministic CQRP services, data models, execution behavior, or the Streamlit administration interface.

## Delivered

- Local React + TypeScript + Vite application in `workstation/`.
- Trader, Portfolio, Research, and Operations workspaces.
- Concurrent panels, KPI cards, responsive layout, sidebar navigation, and `Ctrl+K` command palette.
- Explicit safe empty states: no fabricated market, portfolio, scanner, or broker data.
- Paper/disabled execution labels only.

## Deferred

- Read-only CQRP workstation API.
- Real-time subscriptions and incremental panel refresh.
- Docking, drag/drop, multi-monitor support, charts, grids, and user-saved workspace layouts.
- Any live execution capability.

## Local use

```powershell
cd workstation
npm.cmd install
npm.cmd run dev
```

Run checks with `npm.cmd run test` and `npm.cmd run build`.
