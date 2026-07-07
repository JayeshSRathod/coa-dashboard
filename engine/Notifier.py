"""
Telegram Alerts
----------------
Sends a message via the Telegram Bot API. Credentials come from
st.secrets["telegram"] — never hardcoded, never logged.

Designed to never crash the dashboard: if secrets aren't configured yet,
or the network call fails, this returns False quietly rather than raising.
That means alerts can stay "off by default" until someone deliberately
sets up the bot, with zero risk to the rest of the app.
"""

import requests


def send_telegram_alert(message: str, timeout: int = 5) -> bool:
    try:
        import streamlit as st
        bot_token = st.secrets["telegram"]["bot_token"]
        chat_id = st.secrets["telegram"]["chat_id"]
    except Exception:
        return False

    if not bot_token or not chat_id or "your-telegram" in str(bot_token):
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        resp = requests.post(url, data={"chat_id": chat_id, "text": message}, timeout=timeout)
        return resp.status_code == 200
    except Exception:
        return False


def is_telegram_configured() -> bool:
    try:
        import streamlit as st
        bot_token = st.secrets["telegram"]["bot_token"]
        chat_id = st.secrets["telegram"]["chat_id"]
        return bool(bot_token) and bool(chat_id) and "your-telegram" not in str(bot_token)
    except Exception:
        return False
