# Fyers Data-Only Setup for Paper Trading

CQRP uses FYERS only for market data in the paper-trading phase. It does not send FYERS orders.

1. Create or activate a FYERS API app for data access and set its redirect URI in the FYERS dashboard.
2. Complete the current FYERS interactive authentication flow each trading day and obtain the short-lived access token. FYERS requires daily 2FA and does not support continuous refresh-token sessions under the current retail algo framework.
3. Start `streamlit run dashboard/app.py` and open **Configuration → Fyers**.
4. Securely save `app_id`, `secret_key`, `redirect_uri`, and the daily `access_token`. Do not save a broker PIN or refresh token.
5. Enable Fyers and use **Test Fyers configuration**. `READY` verifies only secure credential presence; it never makes a broker order request.
6. Keep CQRP execution in `PAPER` or `DISABLED`.

The runtime records simulated paper events only.
