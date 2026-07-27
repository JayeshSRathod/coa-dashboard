"""Presentation-only page for append-only manual research observations."""

from __future__ import annotations

from datetime import datetime

from src.research.manual_observations import EVENT_TYPES, ManualObservation, ManualObservationService


def render_observation_page(service: ManualObservationService) -> None:
    import streamlit as st

    st.title("Observation Notes")
    st.caption("Append-only manual evidence for the daily COA review. Notes never change COA, signals, or paper trades.")
    now = datetime.now().astimezone()
    with st.form("manual-observation"):
        left, right = st.columns(2)
        with left:
            session_date = st.date_input("Session date", value=now.date())
            observed_time = st.time_input("Observed time", value=now.time().replace(microsecond=0))
            instrument = st.selectbox("Instrument", ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "OTHER"])
            event_type = st.selectbox("Observation type", EVENT_TYPES)
            scenario_number = st.number_input("COA scenario number (optional)", min_value=1, max_value=18, value=None)
        with right:
            spot = st.number_input("Spot (optional)", value=None, format="%.2f")
            support = st.number_input("Support (optional)", value=None, format="%.2f")
            resistance = st.number_input("Resistance (optional)", value=None, format="%.2f")
            eos = st.number_input("EOS (optional)", value=None, format="%.2f")
            eor = st.number_input("EOR (optional)", value=None, format="%.2f")
        narrative = st.text_area("What happened?", placeholder="Example: Put-side volume built at 23950; OI followed, spot held and re-entered above the migrated support.")
        expected = st.text_area("Expected outcome (optional)")
        actual = st.text_area("Actual outcome (optional)")
        reference = st.text_input("Reference / screenshot note (optional)")
        submitted = st.form_submit_button("Record immutable observation")
    if submitted:
        try:
            observed_at = datetime.combine(session_date, observed_time, tzinfo=now.tzinfo).isoformat()
            observation = ManualObservation(
                observed_at=observed_at, session_date=session_date.isoformat(), instrument=instrument,
                event_type=event_type, narrative=narrative, scenario_number=scenario_number,
                spot=spot, support=support, resistance=resistance, eos=eos, eor=eor,
                expected_outcome=expected or None, actual_outcome=actual or None,
                reference_text=reference or None,
            )
            observation_id = service.record(observation)
            st.success(f"Observation recorded as {observation_id}. It cannot be edited or deleted.")
        except Exception as exc:
            st.error(f"Observation was not recorded: {exc}")
    notes = service.recent(limit=100)
    st.subheader("Recent observations")
    if notes:
        st.dataframe(notes, width="stretch", hide_index=True)
    else:
        st.info("No manual observations have been recorded yet.")
