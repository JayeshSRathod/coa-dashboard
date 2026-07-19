# Developer guide

## Non-negotiable rules

1. Do not change COA mathematics, scenario mapping, EOS/EOR formulas, or risk rules without an ADR and dedicated tests.
2. Keep UI, broker, calculation, and database responsibilities separate.
3. Record new runtime data append-only; preserve replayability.
4. Use `src.common.logging.configure_logging` rather than ad-hoc logger setup.
5. New persistence code belongs behind `src.persistence`.
6. Add focused tests for new deterministic behaviour.
7. Never commit credentials, SQLite research data, logs, or Streamlit secrets.

## Git workflow

Use focused feature commits on `develop-v2`; review changes before merging to `main`.