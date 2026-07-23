# CQRP System Architecture

## Core flow

```text
Market provider → canonical market data → snapshot store → frozen COA
→ validation → signal → portfolio risk → paper execution / OMS
→ analytics, journal, research knowledge, dashboard, offline Copilot
```

## Boundaries

| Boundary | Responsibility | Must not do |
| --- | --- | --- |
| `engine/coa_math.py` | Frozen COA baseline mathematics | UI, database, broker actions |
| `src/market_data` / research capture | Normalize and persist market observations | Trading decisions |
| `src/coa`, `src/validation`, `src/decision` | Deterministic analysis and eligibility | Direct SQL or live order placement |
| `src/enterprise_risk`, `src/paper_trading`, `src/oms` | Risk assessment, simulation, OMS safety | Modify frozen COA rules |
| `src/persistence` | Append-only data repositories and migrations | Business decisions |
| `dashboard`, `workstation`, `src/api`, `src/application` | Presentation and serializable service contracts | Trading formulas or direct SQL |
| `src/copilot` | Evidence-grounded advisory summaries | Orders, strategy changes, risk overrides |

## Non-negotiable rules

- Research records are append-only and versioned.
- Dashboard and UI code consume service/repository contracts only.
- The same historical inputs must reproduce the same deterministic core outputs.
- Secrets stay outside Git and SQLite plaintext fields.
- `DISABLED` and `PAPER` remain the safe default modes.
