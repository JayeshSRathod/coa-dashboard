# CQRP Research Governance

The Research Lab evaluates whether a strategy improves risk-adjusted returns. It is not an automatic optimization or deployment system.

## Lifecycle

```text
Idea → strategy version → immutable configuration and dataset → replay/backtest
→ walk-forward / robustness checks → performance review → human approval → production eligibility
```

Grid search, walk-forward validation, Monte Carlo simulation, and benchmarks are deterministic utilities. Their outputs must be associated with a declared dataset, configuration, and strategy version. Results do not change production settings automatically.

Paper-trading findings should be reviewed for scenario, instrument, market regime, time-of-day, liquidity, and expiry effects before any rule change is proposed.
