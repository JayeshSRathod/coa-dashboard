# CQRPDW paper-validation operating plan

CQRPDW is the single operator screen for CQRP during paper validation.  It is
data-only with FYERS and PAPER-only with the CQRP execution engine.  It has no
broker order capability.

## Daily operation

1. Complete FYERS daily authentication, save the token through the local
   launcher, and start the local dashboard and worker.
2. Confirm CQRPDW shows a fresh FYERS timestamp and `PAPER_ONLY` mode.
3. For every `PAPER_BUY` or `PAPER_SELL`, record the displayed rationale,
   entry, stop, T1 and T2 as the decision evidence for that trade.
4. Monitor the paper phase: `ENTRY_PENDING`, `IN_TRADE`,
   `T1 COMPLETED`, or `EXITED`.  The lifecycle table is the system record;
   do not edit it manually.
5. At session end, preserve the local research database and review realised
   and unrealised P&L, MFE, MAE, exit reason, and the decision rationale.

## Phase gates

### Phase 1 — baseline paper operation (one month)

Run the local worker during the intended market session.  Do not alter the
frozen COA mathematics or enable broker orders.  Log operational defects,
missing data, duplicate trades, lifecycle anomalies, and decisions that are
clearly inconsistent with the documented rationale.

### Phase 2 — parameter review and retest (10–15 trading days)

Analyse the retained paper evidence by scenario, confidence band, direction,
entry/exit phase, P&L, MFE/MAE and exit reason.  Make only versioned,
reviewable configuration changes, then repeat paper validation for 10–15
trading days.  Compare results with the baseline; do not tune from an
individual trade.

### Phase 3 — semi-automatic proposal

Only consider a separate semi-automatic workflow after the two paper phases
show stable operation and the following controls are implemented and accepted:

- configured F&O lot sizes, capital limits, and portfolio risk gates;
- multi-instrument/watchlist controls and data-quality monitoring;
- worker restart/health monitoring and a verified audit trail;
- explicit operator approval for every broker order;
- applicable broker/API permissions and regulatory/compliance review.

Semi-automatic trading is not enabled by this plan or by CQRPDW.
