# CQRP implementation instructions

- Treat `engine/coa_math.py` as frozen strategy mathematics.
- Do not alter `app.py`, `engine/`, or `db/ledger.py` in Sprint-001.
- Place shared infrastructure in `src/common/` and persistence boundaries in `src/persistence/`.
- Avoid new third-party dependencies for platform infrastructure.
- Persisted research data must be append-only in future sprints.
- Add or update tests for deterministic code.
- Do not commit secrets, local databases, reports, or log output.