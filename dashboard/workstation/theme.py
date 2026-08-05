"""Shared visual tokens for the feature-flagged CQRP Decision Workstation."""

from __future__ import annotations


def apply_workstation_theme(st: object, *, theme: str = "dark") -> None:
    """Apply a local CSS theme without changing any Streamlit/domain behaviour."""
    palette = {
        "dark": ("#071019", "#0d1a26", "#203447", "#e7eef7", "#91a4b8"),
        "light": ("#f3f7fb", "#ffffff", "#cbd8e6", "#102033", "#52677d"),
    }.get(str(theme).lower(), ("#071019", "#0d1a26", "#203447", "#e7eef7", "#91a4b8"))
    background, panel, border, text, muted = palette
    css = """
        <style>
        :root { --cqrp-bg: __BACKGROUND__; --cqrp-panel: __PANEL__; --cqrp-border: __BORDER__;
                --cqrp-text: __TEXT__; --cqrp-muted: __MUTED__; --cqrp-good: #22c55e;
                --cqrp-warn: #f59e0b; --cqrp-bad: #ef4444; --cqrp-info: #38bdf8; }
        [data-testid="stAppViewContainer"] { background: var(--cqrp-bg); color: var(--cqrp-text); }
        [data-testid="stMainBlockContainer"], .block-container {
            max-width: 100%; padding-top: 1rem; padding-bottom: 1rem;
        }
        .cqrp-card { background: var(--cqrp-panel); border: 1px solid var(--cqrp-border);
                      border-radius: 8px; padding: .45rem .65rem; min-height: 60px; }
        .cqrp-label { color: var(--cqrp-muted); font-size: .78rem; text-transform: uppercase; }
        .cqrp-value { color: var(--cqrp-text); font-size: 1.1rem; font-weight: 650; }
        .cqrp-note { color: var(--cqrp-muted); font-size: .72rem; margin-top: .1rem; }
        .cqrp-badge { display: inline-block; border-radius: 999px; font-size: .75rem;
                       font-weight: 650; padding: .15rem .5rem; }
        .cqrp-good { color: #052e16; background: #86efac; }
        .cqrp-warn { color: #451a03; background: #fde68a; }
        .cqrp-bad { color: #450a0a; background: #fca5a5; }
        .cqrp-info { color: #082f49; background: #7dd3fc; }
        </style>
        """
    for token, value in {
        "__BACKGROUND__": background, "__PANEL__": panel, "__BORDER__": border,
        "__TEXT__": text, "__MUTED__": muted,
    }.items():
        css = css.replace(token, value)
    st.markdown(css, unsafe_allow_html=True)
