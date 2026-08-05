"""Streamlit presentation for local CQRP configuration; no credentials are rendered back."""

from __future__ import annotations

from src.configuration_console.service import ConfigurationConsoleService
from src.configuration_console.secrets import SecretStoreUnavailable
from src.notifications import TelegramNotificationClient


def render_configuration_page(service: ConfigurationConsoleService | None = None) -> None:
    import streamlit as st

    service = service or ConfigurationConsoleService()
    st.title("Configuration")
    st.caption("Credentials are stored only in environment/Streamlit secrets or your local OS credential manager.")
    try:
        state = service.public_configuration()
    except Exception as exc:
        st.error(f"Configuration is unavailable: {exc}")
        return

    broker_tab, telegram_tab, execution_tab, operations_tab, local_ai_tab, history_tab, test_tab = st.tabs(
        ["Broker Settings", "Telegram", "Execution Mode", "Scanner & Risk", "Local AI", "Configuration History", "Test Connections"]
    )
    with broker_tab:
        _render_provider(st, service, state, "dhan", "Dhan", ("client_id", "access_token"))
        st.caption("Fyers is data-only in CQRP. Complete FYERS daily authentication yourself, then save the short-lived access token. Never save a broker PIN or refresh token.")
        _render_provider(st, service, state, "fyers", "Fyers", ("app_id", "secret_key", "redirect_uri", "access_token"))
    with telegram_tab:
        _render_provider(st, service, state, "telegram", "Telegram", ("bot_token", "chat_id"))
        _render_telegram_reporting(st, service, state)
    with execution_tab:
        current = state["execution"]["execution_mode"]
        mode = st.selectbox("Execution mode", ["DISABLED", "PAPER"], index=["DISABLED", "PAPER"].index(current))
        st.info("LIVE execution is intentionally unavailable. Saving always enforces dry-run and kill-switch protections.")
        if st.button("Save execution mode"):
            try:
                st.success(f"Saved {service.save_execution_mode(mode)['execution_mode']} mode.")
            except Exception as exc:
                st.error(f"Execution mode was not saved: {exc}")
    with operations_tab:
        operations = state["operations"]
        with st.form("operations-settings"):
            interval = st.number_input("Scanner interval (seconds)", min_value=1,
                                       value=int(operations["scanner_interval_seconds"]))
            positions = st.number_input("Maximum open paper positions", min_value=0,
                                        value=int(operations["max_open_positions"]))
            submitted = st.form_submit_button("Save scanner and risk settings")
        if submitted:
            try:
                service.save_operations(scanner_interval_seconds=int(interval), max_open_positions=int(positions))
                st.success("Operational settings saved.")
            except Exception as exc:
                st.error(f"Operational settings were not saved: {exc}")
    with local_ai_tab:
        local_ai = state["local_ai"]
        enabled = st.toggle(
            "Enable local Ollama advisory assistant",
            value=bool(local_ai["ollama_enabled"]),
            help="Off by default. When off, CQRP never contacts or loads Ollama; all market capture and paper research continue normally.",
        )
        st.caption("The assistant is read-only and advisory-only. It cannot place orders, alter COA, change risk, or train itself from CQRP data.")
        if st.button("Save local AI setting"):
            try:
                saved = service.save_local_ollama_enabled(enabled)
                status = "ON" if saved["ollama_enabled"] else "OFF"
                st.success(f"Local Ollama advisory is {status}.")
            except Exception as exc:
                st.error(f"Local AI setting was not saved: {exc}")
    with history_tab:
        history = list(reversed(state["history"]))
        if history:
            st.dataframe(history, width="stretch")
        else:
            st.info("No local configuration changes have been recorded yet.")
    with test_tab:
        for provider, label in (("dhan", "Dhan"), ("fyers", "Fyers"), ("telegram", "Telegram")):
            if st.button(f"Test {label} configuration", key=f"test-{provider}"):
                result = service.test_connection(provider)
                message = f"{label}: {result['status']} — {result['message']}"
                (st.success if result["status"] == "READY" else st.warning)(message)


def _render_provider(st, service: ConfigurationConsoleService, state: dict, provider: str,
                     label: str, fields: tuple[str, ...]) -> None:
    broker = state["brokers"][provider]
    with st.expander(label, expanded=False):
        st.caption("Saved credentials are masked and cannot be read back from this page.")
        with st.form(f"{provider}-settings"):
            enabled = st.checkbox("Enabled", value=broker["enabled"], key=f"{provider}-enabled")
            credentials = {}
            for field in fields:
                status = "Saved securely" if broker["credentials"][field] else "Not configured"
                st.caption(f"{field.replace('_', ' ').title()}: {status}")
                credentials[field] = st.text_input(field.replace("_", " ").title(), type="password", key=f"{provider}-{field}")
            submitted = st.form_submit_button(f"Save {label}")
        if submitted:
            try:
                service.save_broker(provider, enabled=enabled, credentials=credentials)
                st.success(f"{label} settings saved. Credentials remain masked.")
            except SecretStoreUnavailable as exc:
                st.error(f"{label} settings were not saved securely: {exc}")
            except Exception as exc:
                st.error(f"{label} settings were not saved: {exc}")


def _render_telegram_reporting(st, service: ConfigurationConsoleService, state: dict) -> None:
    settings = state["telegram_notifications"]
    st.subheader("PAPER research reporting")
    st.caption("Topic IDs are optional. Leave a topic blank to send to the group General topic. "
               "CQRP never sends broker orders or raw credentials through Telegram.")
    with st.form("telegram-reporting-settings"):
        enabled = st.checkbox("Enable Telegram reports", value=bool(settings["enabled"]))
        heartbeat = st.number_input("Health heartbeat (minutes)", min_value=5, max_value=240,
                                    value=int(settings["heartbeat_minutes"]))
        topics = {}
        labels = {
            "system_health": "System Health",
            "market_decisions": "Market & Decisions",
            "preclose_plan": "Pre-Close & Tomorrow Plan",
            "paper_portfolio": "Paper Portfolio",
            "daily_research": "Daily & Weekly Research",
        }
        for key, label in labels.items():
            topics[key] = st.text_input(f"Topic ID — {label}", value=str(settings["topics"].get(key, "")))
        saved = st.form_submit_button("Save Telegram reporting")
    if saved:
        try:
            service.save_telegram_notifications(enabled=enabled, heartbeat_minutes=int(heartbeat), topics=topics)
            st.success("Telegram report routing saved. Credentials remain masked.")
        except Exception as exc:
            st.error(f"Telegram report routing was not saved: {exc}")
    if st.button("Send PAPER-only Telegram test", key="telegram-paper-test"):
        result = TelegramNotificationClient(service).send_test()
        message = f"Telegram test: {result.status} — {result.reason}"
        (st.success if result.status == "SENT" else st.warning)(message)
