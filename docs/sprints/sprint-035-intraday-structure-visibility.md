# Sprint 035 — Intraday Structure Visibility

## Purpose

Make CQRP's already-persisted dynamic COA evidence understandable during and
after a trading session without changing frozen COA calculations.

## Dashboard additions

- Full-session Spot, Support, EOS, Resistance, and EOR trail.
- Dim historical level lines plus clearly labelled current levels.
- Recorded breakout, rejection, retest, re-entry, and five-minute outcome markers.
- CE/PE top-three Volume and OI wall-strike trails, including expiry-aware contract hover details.
- Full-session evidence remains exportable from the existing COA Research and Strike Activity views.

## Quote-data handling

New FYERS/Dhan captures preserve provider bid, ask, IV, and OI-change fields in
the stored option-chain evidence.  CQRP no longer substitutes LTP as both bid
and ask. Missing provider quotes remain explicitly missing; they are not
invented. Bid/ask remains a liquidity and execution-quality observation, not a
replacement for COA structure or a trading instruction.

## Options Analytics ladder

The Options Analytics page presents a CE-left / strike-centre / PE-right
ladder around the ATM strike. It shows captured LTP, bid, ask, bid-ask spread,
volume, OI change, and optional IV/Greeks context. A symmetric CE-versus-PE
chart supports Open Interest, Volume, or OI-change review. Greeks remain
contextual research data; they do not produce an automatic signal.

## Safety

This sprint is presentation and evidence-capture only. It does not alter COA,
validation, risk, paper execution, or broker order behaviour.
