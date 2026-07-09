"""
COA 2.0 — Intraday Delta-OI Momentum Graphing
------------------------------------------------
Tracks Call-side and Put-side OI-change-% as two live series (the "Call
Delta OI Line" and "Put Delta OI Line" from the theory) and classifies
their relationship into the 9 documented tactical scenarios.

Theory's own golden rule: "Never trade COA 2.0 in isolation. Use it as the
final trigger pull to confirm whether a COA 1.0 boundary wall will hold or
give way." This module only produces the confirmation signal — it is not a
replacement for the COA 1.0 structural read in coa_math.py.

Pure functions only — no Streamlit, no I/O. History lives in the caller's
session state (see app.py), since this needs to persist across polls.
"""

import datetime

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except Exception:
    IST = None

MORNING_RACE_START = datetime.time(9, 15)
MORNING_RACE_END = datetime.time(9, 30)
SQUARE_OFF_START = datetime.time(15, 10)


def compute_side_oi_change_pct(current_total_oi: float, prev_total_oi: float) -> float:
    """One reading of the Call or Put Delta-OI line, as a % change."""
    if not prev_total_oi:
        return 0.0
    return ((current_total_oi - prev_total_oi) / prev_total_oi) * 100


def classify_line_state(history_pct: list, fixed_threshold: float = 15.0,
                         relative_multiplier: float = 3.0) -> str:
    """
    Classifies the most recent reading in history_pct (oldest first) as
    STABLE, SCREAMING_UP, FLEEING_DOWN, or VOLATILE.

    Combines both requested threshold styles: an absolute per-poll % move
    (fixed_threshold) OR a move that's large relative to this line's own
    recent average magnitude (relative_multiplier x rolling average, default
    3x) — either one alone is enough to count as "screaming"/"fleeing". The
    3x default keeps small baseline noise (a 1.6x wobble on a near-zero
    average) from being misread as a genuine shift.

    VOLATILE catches the theory's "erratic and choppy" description (Scenario
    7's call line) — the sign flipping across recent polls rather than
    trending consistently.
    """
    if not history_pct:
        return "STABLE"

    current = history_pct[-1]

    if len(history_pct) >= 3:
        recent = history_pct[-3:]
        if all(abs(v) > 2.0 for v in recent):
            signs = [1 if v > 0 else -1 for v in recent]
            if signs[0] != signs[1] or signs[1] != signs[2]:
                return "VOLATILE"

    prior = history_pct[:-1]
    rolling_avg_abs = (sum(abs(v) for v in prior) / len(prior)) if prior else 0.0
    is_extreme = (
        abs(current) >= fixed_threshold
        or (rolling_avg_abs > 0 and abs(current) >= relative_multiplier * rolling_avg_abs)
    )

    if not is_extreme:
        return "STABLE"
    return "SCREAMING_UP" if current > 0 else "FLEEING_DOWN"


def _now_ist() -> datetime.datetime:
    return datetime.datetime.now(IST) if IST else datetime.datetime.now()


def classify_tactical_scenario(call_state: str, put_state: str, now: datetime.datetime = None) -> dict:
    """
    Maps (call_line_state, put_line_state) to one of the 9 documented COA 2.0
    tactical scenarios. Scenarios 8 and 9 are time-gated per the theory
    ("Morning Race" 9:15-9:30, post-3:10 PM squaring-off) — outside those
    windows, the same both-screaming/both-fleeing pattern is reported as an
    unusual-but-plain reading rather than forcing a time-specific label that
    doesn't actually apply.
    """
    if now is None:
        now = _now_ist()
    t = now.time()
    in_morning_race = MORNING_RACE_START <= t <= MORNING_RACE_END
    in_square_off = t >= SQUARE_OFF_START

    both_screaming = call_state == "SCREAMING_UP" and put_state == "SCREAMING_UP"
    both_fleeing = call_state == "FLEEING_DOWN" and put_state == "FLEEING_DOWN"

    if both_screaming and in_morning_race:
        return {"number": 8, "name": "Morning race", "action": "WAIT",
                "dynamics": "Initial capital deployment (9:15-9:30). Wait for one line "
                            "to break before trading in either direction."}
    if both_fleeing and in_square_off:
        return {"number": 9, "name": "Intraday squaring-off", "action": "STAND_ASIDE",
                "dynamics": "Post-3:10 PM risk dumping. Step aside — behavior is "
                            "unpredictable this late in the session."}

    if call_state == "STABLE" and put_state == "STABLE":
        return {"number": 1, "name": "Both flat / parallel", "action": "RANGE_TRADE",
                "dynamics": "Consolidation around this strike — good for mean-reversion "
                            "trades at the exact boundaries."}
    if put_state == "STABLE" and call_state == "SCREAMING_UP":
        return {"number": 2, "name": "Call screaming, put stable", "action": "SELL",
                "dynamics": "Aggressive call writing. Expect a break past current support."}
    if call_state == "SCREAMING_UP" and put_state == "FLEEING_DOWN":
        return {"number": 3, "name": "Call up, put fleeing", "action": "SHORT",
                "dynamics": "Institutional capitulation — severe bearish acceleration."}
    if call_state == "STABLE" and put_state == "SCREAMING_UP":
        return {"number": 4, "name": "Put screaming, call stable", "action": "BUY_BREAKOUT",
                "dynamics": "Put writing expansion fortifies the floor, forcing a breakout higher."}
    if put_state == "STABLE" and call_state == "FLEEING_DOWN":
        return {"number": 5, "name": "Call fleeing, put stable", "action": "BUY_DRIFT",
                "dynamics": "Call short-covering — steady, low-velocity bullish drift."}
    if put_state == "SCREAMING_UP" and call_state == "FLEEING_DOWN":
        return {"number": 6, "name": "Put up, call fleeing", "action": "BUY_AGGRESSIVE",
                "dynamics": "Explosive bullish flight — call sellers trapped in a short squeeze."}
    if put_state == "FLEEING_DOWN" and call_state == "VOLATILE":
        return {"number": 7, "name": "Put fleeing, call erratic", "action": "SELL_RALLIES",
                "dynamics": "Floor pulled out. Sell counter-trend rallies from the top boundary."}
    if both_screaming:
        return {"number": 8, "name": "Both screaming (outside race window)", "action": "WAIT",
                "dynamics": "Heavy two-sided buildup outside 9:15-9:30 — unusual; "
                            "wait for one side to break before acting."}
    if both_fleeing:
        return {"number": 9, "name": "Both fleeing (outside square-off window)", "action": "WAIT",
                "dynamics": "Two-sided unwinding outside the post-3:10 window — unusual; "
                            "treat cautiously rather than as standard squaring-off."}

    return {"number": 0, "name": "No clean pattern match", "action": "WAIT",
            "dynamics": f"Call={call_state}, Put={put_state} — mixed signal, no clear "
                        f"COA 2.0 confirmation yet."}
