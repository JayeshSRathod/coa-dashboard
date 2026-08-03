# EXP-0001: Market-Data Confirmation Study

## Decision this experiment supports

Decide, using CQRP's own chronological paper-trading evidence, whether any of
the following provider fields should become a permanent validation input,
execution-quality filter, or dashboard feature:

1. Bid/ask spread and quote quality.
2. Bid/ask quantity (market depth) and quote velocity.
3. Short-window volume and open-interest change at the relevant option strike.
4. Provider-supplied option Greeks.
5. Additional index mappings for BANKNIFTY and FINNIFTY.

This is an evidence study, **not a strategy change**. Until an item passes its
promotion gate, it must not change frozen COA mathematics, signal eligibility,
risk sizing, paper execution, or automated behaviour.

## Baseline

The control is the current CQRP pipeline:

```text
FYERS option-chain snapshot -> frozen COA -> validation -> research signal
-> paper-trading simulation -> immutable outcome
```

All control and study observations must retain the same strategy version,
configuration fingerprint, instrument, expiry, scenario, session time and
market snapshot identifier. This prevents a later field from being credited
for a difference caused by a different market, expiry, or configuration.

## Pre-registered hypotheses

| ID | Hypothesis | Expected use if supported | It must not be used for |
|---|---|---|---|
| H1 | A captured bid/ask spread improves simulated fill and cost estimates. | Liquidity/execution-quality filter. | Directional COA prediction by itself. |
| H2 | Actual bid/ask quantities and quote velocity improve five-minute classification of a breakout, rejection, retest or re-entry. | Optional confirmation evidence. | A replacement for price, Volume, OI or COA. |
| H3 | Strike-level volume-first/OI-later patterns reduce false breakouts or improve target-before-stop outcomes. | A future, separately versioned validation component. | Retrospective changes to the current session. |
| H4 | Provider Greeks are sufficiently present and internally consistent to be reliable contextual risk/strike data. | Context and later risk analysis. | A directional signal or automatic trade rule. |
| H5 | Explicit FYERS symbol mappings for BANKNIFTY and FINNIFTY increase clean sample size without reducing data quality. | Multi-index collection scope. | Guessed symbols or copied NIFTY results. |

## Provider-availability audit (Phase A)

Before storing a new field at scale, create a small, sanitized provider sample
for each target instrument and selected option expiry. Record **presence and
quality only**; never record credentials.

| Field | Source to verify | Availability decision |
|---|---|---|
| LTP, volume, OI, OI change, IV, bid, ask | Existing FYERS option-chain response | Measure coverage per strike and expiry. |
| Bid/ask quantities, market depth, quote timestamp | FYERS Market Depth API or Data WebSocket depth payload | Do not implement until an actual payload, entitlement and timestamp semantics are verified. |
| Delta, gamma, theta, vega | FYERS option-chain response | Measure coverage, type/range validity and refresh behaviour. |
| NIFTY, BANKNIFTY, FINNIFTY symbols and expiries | FYERS current symbol master | Register explicit mappings only; no guessed symbols. |

The audit must record: provider endpoint or stream name, observed field names,
response timestamp, received timestamp, instrument, expiry, sample count,
field-coverage percentage, null/malformed count, and measured latency. It is a
data-quality report, not a trading report.

FYERS documents that its option-chain view can expose LTP, OI, IV, volume,
bid/ask and Greeks, while Market Depth/Data WebSocket services may expose
market-depth bid/ask data. CQRP will verify the exact payload and account
availability before relying on either feature. [FYERS option-chain guide](https://support.fyers.in/portal/en/kb/articles/quick-start-guide-for-options-chain-on-fyers)
[FYERS Data API guide](https://support.fyers.in/portal/en/kb/fyers-api-integrations/fyers-api/api-v3/data-api)

## Shadow collection (Phase B)

After Phase A succeeds, collect the extra fields alongside the baseline. The
study is append-only and must preserve every eligible observation, including
missing fields and no-trade outcomes.

### Sampling plan

- Option-chain/structure cadence remains the approved FYERS-safe cadence
  (currently 5/10/16 seconds according to the selected operating mode).
- Depth or quote-velocity sampling, if authorised, begins only around a
  registered structure event or paper candidate; it must not silently change
  the baseline polling cadence.
- Persist the selected contract label including instrument, expiry, strike and
  CE/PE side, for example `NIFTY 24000 CE 28-Jul`.
- Capture the raw provider timestamp and ingestion timestamp so stale quotes
  can be excluded from analysis.
- A missing extra field is a recorded `NOT_AVAILABLE` observation, never a
  substituted value such as LTP used as bid or ask.

### Required labels

For each relevant event or candidate, derive only after the observation window
has ended:

- five-minute breakout sustain, false breakout, rejection, retest or re-entry;
- target-1-before-stop, stop-before-target-1, neither, and time/session exit;
- MAE, MFE, holding duration and net simulated P&L after the configured spread,
  slippage and transaction-cost policy;
- scenario, dynamic support/resistance/EOS/EOR movement, CE/PE wall migration,
  and data-quality status.

## Analysis design (Phase C)

1. Use chronological, completed paper-trade or event labels only. Never use a
   future outcome to construct a feature at decision time.
2. Compare observations within the same instrument, expiry type, time bucket,
   COA scenario, configuration and market regime where possible.
3. Report both **directional** outcomes (false-break rate, five-minute outcome,
   target-before-stop) and **execution** outcomes (spread cost, fill realism,
   MAE/MFE and net P&L). H1 can pass as an execution improvement without being
   a directional predictor.
4. Keep all no-trade, rejected and missing-data observations. Removing them
   would create selection bias.
5. Produce a weekly immutable report; parameter changes may be proposed only
   after a human review of the report and walk-forward evidence.

## Promotion gates

No field is promoted simply because it looks useful in a single day. A proposed
promotion needs all of the following:

1. **Availability:** documented provider payload and at least 90% valid
   coverage for the eligible liquid contracts/sessions being assessed.
2. **Quality:** no unaccounted timestamp inversion, stale-quote problem or
   material instrument/expiry mapping error.
3. **Sample:** at least 50 comparable completed labels for a narrow pilot; 100
   or more before changing a production-facing validation rule. Smaller samples
   remain exploratory.
4. **Incremental evidence:** improvement versus the frozen baseline in the
   pre-registered outcome relevant to that feature, with no material worsening
   of drawdown, trade count or data-loss rate.
5. **Robustness:** the effect is visible across more than one session and is
   reviewed by instrument, expiry and time of day rather than inferred from a
   single favourable run.
6. **Governance:** a new ADR, configuration version, deterministic tests and a
   human-approved strategy/validation version are required before promotion.

If any gate fails, retain the field only as optional research evidence or stop
collecting it. CQRP will not add a cosmetic table, chart or trading condition.

## Greek-specific rule

Provider Greeks are assessed first for coverage, timestamp freshness, range
validity and stability. An independent Greek calculation is justified only if
the provider values are materially missing, stale or inconsistent in the
measured study. If that occurs, the calculation must document its pricing
assumptions (risk-free rate, dividend assumptions, volatility source and time
to expiry) and be validated separately. It is not an automatic predictor.

## Multi-index rule

NIFTY, BANKNIFTY and FINNIFTY are separate instruments. CQRP must obtain and
version their symbol/expiry mappings from FYERS' current symbol master before
manual fetch or automatic capture is enabled for them. The FYERS symbol-master
files are the provider's supported source for current symbols. [FYERS symbol-master guidance](https://support.fyers.in/portal/en/kb/articles/where-can-i-get-the-symbol-list-in-fyers-api-v3)

Each index must receive its own capture count, expiry records, field-coverage
report and outcome analysis. NIFTY observations must never be displayed as
BANKNIFTY or FINNIFTY evidence.

## Deliverables and decision record

Phase A produces a provider-availability report. Phase B produces immutable
shadow observations. Phase C produces a comparison report with one decision per
hypothesis:

```text
PROMOTE -> separately versioned implementation
RETAIN AS RESEARCH -> continue observing; no trading impact
REJECT -> do not add to CQRP
```

The next engineering work is therefore a **small provider-availability probe**
and evidence report, not production market-depth, independent-Greeks, or
multi-index trading implementation.

## Current Phase-A utility

CQRP includes a deterministic local audit utility that reads existing immutable
snapshots and reports captured field coverage by instrument and expiry:

```powershell
python scripts/audit_market_data.py database/cqrp_research.db NIFTY
# Audit only the most recent capture window, avoiding historical fields
# that did not exist before the current capture version.
python scripts/audit_market_data.py database/cqrp_research.db NIFTY --latest 100
```

It reports bid, ask, OI-change, IV and provider-Greek coverage, plus snapshot
quality. A `true` availability gate only means that the captured quote fields
are sufficiently present to justify a shadow study; it is explicitly **not** a
claim of profitable predictive value.
