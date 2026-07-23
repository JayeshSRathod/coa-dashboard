# CQRP Operations Runbook

## Normal start

1. Use an isolated Python environment.
2. Install `requirements.txt`.
3. Keep broker credentials in Streamlit secrets, environment variables, or the approved local secret store.
4. Verify execution mode is `DISABLED` or `PAPER`.
5. Start the current dashboard with `streamlit run dashboard/app.py`.

## Daily safety checks

- Confirm market-data source freshness and data quality.
- Confirm broker and notification status without exposing credentials.
- Confirm the database backup location and available disk capacity.
- Review risk/exposure limits and OMS safety state.
- Treat any missing or degraded data as a reason to pause paper/live workflows.

## Incident rule

If data quality, broker synchronization, risk controls, or auditability is uncertain, set/keep execution `DISABLED`, preserve logs and records, and investigate before continuing.
