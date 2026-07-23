"""Streamlit presentation for local CQRP configuration; no credentials are rendered back."""

from __future__ import annotations

from src.configuration_console.service import ConfigurationConsoleService
from src.configuration_console.secrets import SecretStoreUnavailable


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

    broker_tab, telegram_tab, execution_tab, operations_tab, history_tab, test_tab = st.tabs(
        ["Broker Settings", "Telegram", "Execution Mode", "Scanner & Risk", "Configuration History", "Test Connections"]
    )
    with broker_tab:
        _render_provider(st, service, state, "dhan", "Dhan", ("client_id", "access_token"))
        st.caption("Fyers is data-only in CQRP. Complete FYERS daily authentication yourself, then save the short-lived access token. Never save a broker PIN or refresh token.")
        _render_provider(st, service, state, "fyers", "Fyers", ("app_id", "secret_key", "redirect_uri", "access_token"))
    with telegram_tab:
        _render_provider(st, service, state, "telegram", "Telegram", ("bot_token", "chat_id"))
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
    with history_tab:
        history = list(reversed(state["history"]))
        if history:
            st.dataframe(history, use_container_width=True)
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
