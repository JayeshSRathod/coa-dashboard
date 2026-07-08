"""
Instrument Registry
--------------------
Central place for per-instrument config. Add a new index here and it shows
up in the dashboard automatically — no other code changes needed.

step_size    : strike interval used for the COA imaginary-line axis
expiry_type  : "weekly" (has a near weekly expiry) or "monthly" (monthly only)
exchange     : broker/exchange segment — matters once real DhanHQ data is wired in
security_id  : Dhan's exact instrument ID — verified against Dhan's own
               instrument master CSV (https://images.dhan.co/api-data/api-scrip-master.csv),
               not guessed. A wrong ID here silently pulls the wrong instrument's data.
dhan_segment : Dhan's "UnderlyingSeg" API parameter. All indices (NSE and BSE
               alike) use "IDX_I" per Dhan's exchange-segment enum — confirmed
               from https://dhanhq.co/docs/v2/annexure/
fyers_symbol : Fyers' symbol format for the option chain API. Cross-checked
               across multiple community SDK sources (Fyers' own docs pages
               are a JS app that couldn't be fetched directly) — treat with
               slightly less certainty than the Dhan IDs above; verify against
               the raw response using the debug toggle the first time you use it.

Notes on current expiry rules (SEBI, effective Nov 2024 / Sept 2025):
  - NIFTY 50 : weekly (Tuesday) + monthly, on NSE
  - BANKNIFTY: monthly only, on NSE (weekly discontinued Nov 2024)
  - FINNIFTY : monthly only, on NSE (weekly discontinued Nov 2024)
  - SENSEX   : weekly (Thursday) + monthly, on BSE

Lot sizes are deliberately NOT hardcoded here — they're revised periodically
by SEBI/exchange notional-value rules. Pull them from the broker's
instrument master when wiring up real orders, don't rely on a fixed number.
"""

INSTRUMENTS = {
    "NIFTY 50": {
        "ticker": "NSE_INDEX|Nifty 50",
        "exchange": "NSE",
        "step_size": 50,
        "expiry_type": "weekly",
        "default_spot": 24440.85,
        "security_id": 13,
        "dhan_segment": "IDX_I",
        "fyers_symbol": "NSE:NIFTY50-INDEX",
    },
    "BANK NIFTY": {
        "ticker": "NSE_INDEX|Nifty Bank",
        "exchange": "NSE",
        "step_size": 100,
        "expiry_type": "monthly",
        "default_spot": 51820.40,
        "security_id": 25,
        "dhan_segment": "IDX_I",
        "fyers_symbol": "NSE:NIFTYBANK-INDEX",
    },
    "FINNIFTY": {
        "ticker": "NSE_INDEX|Nifty Fin Service",
        "exchange": "NSE",
        "step_size": 50,
        "expiry_type": "monthly",
        "default_spot": 23150.25,
        "security_id": 27,
        "dhan_segment": "IDX_I",
        "fyers_symbol": "NSE:FINNIFTY-INDEX",
    },
    "SENSEX": {
        "ticker": "BSE_INDEX|Sensex",
        "exchange": "BSE",
        "step_size": 100,
        "expiry_type": "weekly",
        "default_spot": 80250.60,
        "security_id": 51,
        "dhan_segment": "IDX_I",
        "fyers_symbol": "BSE:SENSEX-INDEX",
    },
}


def get_instrument(name: str) -> dict:
    return INSTRUMENTS[name]


def instrument_names() -> list:
    return list(INSTRUMENTS.keys())
