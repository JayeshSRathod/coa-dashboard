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

## Going live (real broker data)

Everything routes through `engine/data_feed.py:get_option_chain()`. Replace
its body with a real DhanHQ REST/WebSocket call that returns the same
columns (`Strike, Call_OI, Call_Vol, Call_LTP, Put_LTP, Put_Vol, Put_OI`) —
nothing else in the app needs to change.

Order placement (turning "Open CALL/PUT position" into a real broker order)
is a separate, higher-risk step — build and test an order-simulation layer
first (log what *would* be sent, without hitting the live endpoint) before
wiring in real execution.
