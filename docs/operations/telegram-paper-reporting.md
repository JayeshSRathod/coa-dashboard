# Telegram PAPER Research Reporting

CQRP's Telegram integration is an opt-in operational reporting channel. It is
not an execution channel: it does not submit FYERS orders, alter COA logic, or
contain broker credentials.

## Configuration

Open **Configuration → Telegram** in the local dashboard.

1. Save the bot token and chat ID through the existing masked credential form.
2. Enable the Telegram provider.
3. Enable **PAPER research reporting**.
4. Set a heartbeat interval (default: 30 minutes).
5. Optionally enter Telegram Topic IDs. Leaving an ID empty sends that class of
   report to the group General topic.
6. Use **Send PAPER-only Telegram test** before market hours.

The bot token and chat ID are stored only by the configured environment,
Streamlit secret store, or operating-system credential manager. Topic IDs and
delivery settings are non-secret local configuration metadata.

## Suggested group topics

| Topic key | Suggested Telegram topic | Current messages |
|---|---|---|
| `system_health` | System Health | market-session start, capture failure, 30-minute heartbeat |
| `market_decisions` | Market & Decisions | reserved for evidence-backed decision changes |
| `preclose_plan` | Pre-Close & Tomorrow Plan | plan recorded in the 15:00–15:20 IST window |
| `paper_portfolio` | Paper Portfolio | simulated paper-trade lifecycle event |
| `daily_research` | Daily & Weekly Research | daily close capture digest |

## Worker behaviour

Start the existing local worker as usual. The worker reads the Telegram setting
at startup and reports only while the regular NSE session is open. On a
session transition to closed, it sends one daily digest. A manual worker stop
also attempts the digest once.

All messages state `PAPER ONLY` where relevant. A simulated paper trade is
never described as a broker order.

## Operational limits

Telegram delivery is deliberately best effort. If Telegram is disabled,
credentials are incomplete, or delivery fails, CQRP continues market capture
and research unchanged. The logger records only the topic and error class—never
the bot token, chat ID, or other raw secret.
