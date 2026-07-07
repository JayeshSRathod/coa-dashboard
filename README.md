# COA Dashboard

## Setup (VS Code / local machine)

```bash
cd COA_Dashboard
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
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

## Going live (real broker data)

Everything routes through `engine/data_feed.py:get_option_chain()`. Replace
its body with a real DhanHQ REST/WebSocket call that returns the same
columns (`Strike, Call_OI, Call_Vol, Call_LTP, Put_LTP, Put_Vol, Put_OI`) —
nothing else in the app needs to change.

Order placement (turning "Open CALL/PUT position" into a real broker order)
is a separate, higher-risk step — build and test an order-simulation layer
first (log what *would* be sent, without hitting the live endpoint) before
wiring in real execution.
