"""
Diversion (UR / US)
---------------------
Per the COA theory: "intraday intermediary pivot zones created when volume
shifts halfway between strike prices." Confirmed interpretation: this is a
pivot triggered specifically by the wall's location migrating from one
strike to another during the session — not a fixed calculation off the
initial DIL. This is the same "wall travels during a rally" behavior
discussed earlier (writers rolling positions as spot pushes through a level).

UR (upper diversion) forms when the resistance wall migrates to a new strike.
US (support-side diversion) forms when the support wall migrates to a new
strike. Each is the midpoint between the OLD wall strike and the NEW one at
the moment of migration.

Pure functions — caller (app.py) tracks the actual wall-strike history in
session state and calls detect_diversion() each poll.
"""


def detect_diversion(prev_strike, current_strike):
    """
    Returns the diversion pivot level if the wall has migrated to a new
    strike since the last poll, else None (no migration this poll).

    prev_strike is None on the very first poll of a session — nothing to
    compare against yet, so no diversion can be detected.
    """
    if prev_strike is None or current_strike == prev_strike:
        return None
    return (prev_strike + current_strike) / 2.0
