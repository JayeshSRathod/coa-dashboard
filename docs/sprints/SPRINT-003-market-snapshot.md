# Sprint-003 — Market Snapshot Capture & Replay

## Goal

Capture, validate, persist, and replay immutable market snapshots independently of the Streamlit dashboard and frozen COA engine.

## Components

- provider-neutral `MarketSnapshotPayload` contract
- `SnapshotCaptureService` and optional polling service
- deterministic `SnapshotValidator`
- `SnapshotRepository` for all snapshot/event persistence and reads
- UI-independent `ReplayService`
- structured log events and in-memory capture metrics

## Persistence

Migration v2 adds session, market/ingestion timestamps, futures/ATM/expiry metadata, completeness, missing-strike, and provider metadata fields to the existing append-only `market_snapshots` event table.

## Explicitly out of scope

No dashboard integration, no broker API adapter, no COA calculation changes, no live order placement, and no strategy execution from replay.