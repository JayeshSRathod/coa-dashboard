# FYERS data configuration for CQRPDW

CQRP currently uses FYERS only for read-only data and PAPER research. It does
not place, prepare, or transmit broker orders.

## Required FYERS setup

1. Create or open your app in the FYERS API Dashboard.
2. Set a redirect URL that matches the CQRP token flow.
3. Enable **Quotes & Market Data** and **Historical Data** permissions. These
   permissions are required for the present index paper worker and for the
   planned equity/history technical-data adapter.
4. Store the App ID, Secret Key, Redirect URI, and daily access token through
   the CQRP local launcher/OS credential manager. Never put them in source
   code or a committed configuration file.

FYERS documents that its clients can access historical, quote, and real-time
market data through API V3 without a separate data-feed subscription. Access
still depends on a valid FYERS account, a created app, selected permissions,
and a valid authenticated session.

## Configured index universe

The local paper worker defaults to:

```text
NIFTY,BANKNIFTY,FINNIFTY
```

To temporarily reduce or change the supported set, set this environment
variable before starting the worker:

```powershell
$env:CQRP_FYERS_INDEX_UNIVERSE = "NIFTY,BANKNIFTY"
```

Valid names are `NIFTY`, `BANKNIFTY`, and `FINNIFTY`. CQRP deliberately
rejects unknown names rather than making a request for an unverified symbol.

## Equity / stock scanning

The current worker is an option-chain worker. Equity scanning needs a separate
FYERS Quotes/History or Data-WebSocket adapter, symbol-master validation, and
an explicitly selected stock universe. It must not be simulated by sending an
equity symbol to the option-chain endpoint.
