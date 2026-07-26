# Local FYERS + PAPER Launcher

Use `scripts\Start-CQRP-Local.cmd` for the local CQRP workflow. It is a guided Windows launcher, not a trading terminal.

1. Double-click `Start-CQRP-Local.cmd` from File Explorer.
2. Choose whether to generate today's daily FYERS token.
3. Complete FYERS login and 2FA when prompted. The launcher saves the returned daily token, app ID, secret key, and redirect URI to the local operating-system credential store; it does not display or copy the token.
4. The launcher opens the local dashboard at `http://localhost:8501` only after that secure save completes.
5. Return to the launcher and press Enter. It starts the data-only FYERS worker at a 60-second interval.

The worker captures only on NSE weekdays from 09:15 through 15:30 IST. Each capture is processed through the snapshot, COA, validation, signal, and PAPER-trade flow. It never submits FYERS orders.

The local worker and local dashboard share the local CQRP research database. The Streamlit Cloud dashboard cannot read that database.
