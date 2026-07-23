# COA Dashboard / CQRP

CQRP is a research-first COA platform. The current documentation index is [docs/README.md](docs/README.md); it covers architecture, research governance, operations, and safe local use.

## CQRP 3.0 workstation (local preview)

The panel-based CQRP 3.0 workstation is a separate local React application.
It is currently a safe presentation foundation: it has no broker order path,
shows only `PAPER` or `DISABLED` execution state, and does not replace the
Streamlit configuration and diagnostics interface.

```powershell
cd workstation
npm.cmd install
npm.cmd run dev
```

See `docs/sprints/cqrp-3.0-workspace-foundation.md` for the current scope.

## Setup (VS Code / local machine)

```bash
cd COA_Dashboard
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run dashboard/app.py
```

Opens at http://localhost:8501

## Project layout

```
COA_Dashboard/
├── app.py                    # Streamlit UI — Live signals + Trade history
├── engine/
│   ├── coa_math.py           # Support/resistance/vector/scenario logic (pure, unit-testable)
│   └── data_feed.py          # Simulated chain generator — swap for real DhanHQ calls here
├── db/
│   └── ledger.py             # SQLite: open/close trades, history + win-rate queries
├── tests/
│   └── test_coa_math.py      # Run: python tests/test_coa_math.py
├── requirements.txt
└── coa_trading_ledger.db     # created automatically on first run
```

## What's on each screen

**Live signals**
- Support/resistance walls, current scenario, risk mode
- Near-the-money strike ladder, shaded by volume change since the last poll
- Active trade card: entry/SL/T1/T2, live P&L, what you'd lose if SL hit,
  risk:reward, and a one-line rationale for why the setup fired
- Scenario win-rate line ("hit T1 in 9 of 14 setups") — this is pulled live
  from your own logged trade history, so it starts blank until you've closed
  a few trades and becomes meaningful after 20–30
- If no trade is open: the probable CALL/PUT setups with their levels, and
  buttons to open a (virtual) position

**Trade history**
- Adjustable window (default 30 days) via the sidebar slider
- Total trades, net P&L, win rate, wins/losses
- Equity curve (cumulative P&L over time)
- Win rate broken down by scenario type
- Full closed-trade table (entry, exit, SL, T1, T2, exit reason, P&L)

## Pushing to GitHub / deploying without a local machine

- `.gitignore` already excludes `coa_trading_ledger.db`, `__pycache__/`, `venv/`,
  and any `.env` / `secrets.toml` — so pushing the repo won't leak trade data
  or credentials.
- `.streamlit/secrets.toml.example` shows the shape of the secrets file.
  Copy it to `.streamlit/secrets.toml` locally (git-ignored) for testing,
  or paste its filled-in contents into **Streamlit Community Cloud → App
  settings → Secrets** when deploying — never commit real keys.
- To deploy: push this repo to GitHub, then go to share.streamlit.io →
  "New app" → point it at the repo and `app.py`. It installs
  `requirements.txt` automatically and gives you a public URL that also
  works fine on a phone browser.

## Setting up Telegram alerts

1. **Create a bot**: open Telegram, message **@BotFather**, send `/newbot`, follow the
   prompts. It gives you a **bot token** (looks like `123456789:AAF...`).
2. **Get your chat ID**: message your new bot anything first (so it has a
   conversation to reply to), then visit in a browser:
   `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   Look for `"chat":{"id": ...}` in the response — that number is your chat ID.
3. **Add credentials to secrets**:
   - Locally: copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`
     and fill in the real `bot_token` and `chat_id` under `[telegram]`
   - On Streamlit Cloud: paste the same content into **App settings → Secrets**
     (never commit the real values to GitHub)
4. Reboot the app. The sidebar should show **"Bot configured"** — tap
   **"Send test alert"** to confirm it reaches your phone, then flip on
   **"Enable alerts"**.

You'll get a Telegram message when: the scenario changes for the currently
selected instrument, a CALL/PUT position is opened, and when a trade is
closed (T1/T2 hit or force square-off).

## Setting up live Fyers data (all four indices)

This is a one-time setup with several steps — take them in order.

**1. Create a Fyers API app**
- Go to [myapi.fyers.in/dashboard](https://myapi.fyers.in/dashboard/), log in, click "Create App"
- Fill in an App Name and a Redirect URL (any URL works, e.g. `https://www.google.com` — you just need to read the `auth_code` off it once)
- Save. Note the **App ID** and **Secret Key** it gives you.

**2. Enable TOTP 2FA** (required to log in programmatically)
- Go to [myaccount.fyers.in/ManageAccount](https://myaccount.fyers.in/ManageAccount)
- Enable "External 2FA TOTP", scan the QR code with an authenticator app

**3. Generate the initial auth code (one-time, needs a browser)**
- Using the `fyers-apiv3` Python package, generate a login URL, open it, log in with your Fyers credentials + TOTP, approve the app
- After approval, you're redirected to your Redirect URL with `auth_code=...` in the address bar — copy that value

**4. Exchange the auth code for a refresh token**
- Use the auth_code + App ID + Secret Key to call Fyers' token exchange — this returns both an `access_token` (valid ~1 day) and a `refresh_token` (longer-lived)
- **The `refresh_token` is what you need for secrets** — this is what lets the app get new access tokens automatically without repeating steps 2–3 every day

**5. Add to Streamlit secrets:**
```toml
[fyers]
app_id = "your-real-app-id"
secret_key = "your-real-secret-key"
refresh_token = "your-real-refresh-token"
```

**Security note**: CQRP must never store a broker PIN. Use a short-lived or
manually refreshed session token where a broker requires interactive PIN or
TOTP confirmation. Do not commit any credential or add it to SQLite.

**6.** Reboot the app. If Fyers is configured, the sidebar shows a **"Use
live data"** checkbox with a caption confirming the priority order
(**Fyers → Dhan → manual**, if both are set up), plus a **"Show raw Fyers
response (debug)"** option — turn debug on the first time you test, since
the exact response parsing was built from community-verified sources
(Fyers' own docs are a JS app we couldn't fetch directly), not a primary
source. If the spot price or OI/volume numbers look wrong, the raw view
will show you why.

**To also enable the Dhan fallback**, add its secrets alongside Fyers'
(same secrets box):
```toml
[dhan]
client_id = "your-real-dhan-client-id"
access_token = "your-real-dhan-access-token"
```
This requires Dhan's Data API subscription (₹499/month) to actually work —
if you don't have that active, leave the `[dhan]` section out and the app
will fall straight to manual entry if Fyers fails, which is a perfectly
reasonable choice if you'd rather not pay for a fallback you rarely need.

If both live sources fail (or aren't configured), the dashboard
automatically falls back to manual spot entry rather than crashing.

**Scope note**: the live toggle only affects the Live Signals page for the
currently selected instrument. The Momentum Leaderboard page still uses
simulated data for all four instruments.

## Going live (real broker data)

Everything routes through `engine/fyers_feed.py:get_live_fyers_chain()` and
`engine/fyers_auth.py:refresh_fyers_access_token()` for the primary path,
and `engine/data_feed.py:get_live_chain()` for the Dhan fallback path — both
are fully wired into `app.py`'s three-tier fallback chain.

Order placement (turning "Open CALL/PUT position" into a real broker order)
is a separate, higher-risk step — build and test an order-simulation layer
first (log what *would* be sent, without hitting the live endpoint) before
wiring in real execution.
