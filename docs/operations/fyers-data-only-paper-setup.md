# Fyers Data-Only Setup for Paper Trading

CQRP uses FYERS only for market data in the paper-trading phase. It does not send FYERS orders.

1. Create or activate a FYERS API app for data access and set its redirect URI in the FYERS dashboard.
2. Complete the current FYERS interactive authentication flow each trading day and obtain the short-lived access token. FYERS requires daily 2FA and does not support continuous refresh-token sessions under the current retail algo framework.
3. Start `streamlit run dashboard/app.py` and open **Configuration → Fyers**.
4. Securely save `app_id`, `secret_key`, `redirect_uri`, and the daily `access_token`. Do not save a broker PIN or refresh token.
5. In **Market Intelligence**, use **Fetch live FYERS option chain**. This makes one explicit, read-only market-data request; it never sends a broker order. A successful response confirms the daily session is active.
6. Keep CQRP execution in `PAPER` or `DISABLED`.

For Streamlit Cloud secrets, use the Dashboard 2.0 flat key names (not a `[fyers]` TOML section):

```toml
CQRP_FYERS_APP_ID = "..."
CQRP_FYERS_SECRET_KEY = "..."
CQRP_FYERS_REDIRECT_URI = "..."
CQRP_FYERS_ACCESS_TOKEN = "..."
```

## Generate a daily access token locally

When the FYERS application's registered redirect URI is `http://localhost:8501`, use the interactive helper from the repository root. It uses only the existing `requests` dependency; no FYERS SDK or C++ build tools are needed:

```powershell
.\venv\Scripts\Activate.ps1
python .\generate_fyers_token.py
```

Stop a locally running Streamlit process first so port 8501 is free. Complete FYERS login in the displayed URL and keep the PowerShell window open. The helper temporarily listens on port 8501, receives the redirect automatically, and shows a confirmation page instead of a localhost error. Do not paste tokens into chat, source files, or Git.

The runtime records simulated paper events only.
