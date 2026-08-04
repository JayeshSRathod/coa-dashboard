"""Shared visual tokens for the feature-flagged CQRP Decision Workstation."""

from __future__ import annotations


def apply_workstation_theme(st: object) -> None:
    """Apply a local CSS theme without changing any Streamlit/domain behaviour."""
    st.markdown(
        """
        <style>
        :root { --cqrp-bg: #071019; --cqrp-panel: #0d1a26; --cqrp-border: #203447;
                --cqrp-text: #e7eef7; --cqrp-muted: #91a4b8; --cqrp-good: #22c55e;
                --cqrp-warn: #f59e0b; --cqrp-bad: #ef4444; --cqrp-info: #38bdf8; }
        .cqrp-card { background: var(--cqrp-panel); border: 1px solid var(--cqrp-border);
                      border-radius: 10px; padding: .75rem 1rem; min-height: 88px; }
        .cqrp-label { color: var(--cqrp-muted); font-size: .78rem; text-transform: uppercase; }
        .cqrp-value { color: var(--cqrp-text); font-size: 1.25rem; font-weight: 650; }
        .cqrp-note { color: var(--cqrp-muted); font-size: .78rem; margin-top: .2rem; }
        .cqrp-badge { display: inline-block; border-radius: 999px; font-size: .75rem;
                       font-weight: 650; padding: .15rem .5rem; }
        .cqrp-good { color: #052e16; background: #86efac; }
        .cqrp-warn { color: #451a03; background: #fde68a; }
        .cqrp-bad { color: #450a0a; background: #fca5a5; }
        .cqrp-info { color: #082f49; background: #7dd3fc; }
        </style>
        """,
        unsafe_allow_html=True,
    )
