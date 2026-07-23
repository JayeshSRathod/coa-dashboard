# ADR-0022: Trade Decision Engine

Sprint-021 introduces one advisory-only `TradeDecision` object. The engine consumes canonical COA state plus supplied validation, risk and market-quality evidence. It never invokes a broker, changes COA rules, or enables execution. `WAIT` and `NO_TRADE` remain first-class decisions with immutable reasons.
