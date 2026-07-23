"""Explicit structural/tactical compatibility table; never infer a missing combination."""
from .models import CompatibilityResult, StructuralState, TacticalState
def evaluate(structural: StructuralState, tactical: TacticalState) -> CompatibilityResult:
    if structural.risk_mode == "HALT_TRADING": return CompatibilityResult("NO_TRADE", -100.0, "BLOCKED", (), ("Structural scenario is halt-worthy.",))
    if tactical.action in {"WAIT", "STAND_ASIDE"}: return CompatibilityResult("WAIT", -25.0, "LOW", ("fresh_market_data",), ("Tactical state requires waiting.",))
    if structural.direction == "BULLISH" and tactical.action in {"BUY_BREAKOUT", "BUY_DRIFT", "BUY_AGGRESSIVE", "RANGE_TRADE"}: return CompatibilityResult("BUY", 10.0 if tactical.action == "BUY_AGGRESSIVE" else 0.0, "AGGRESSIVE" if tactical.action == "BUY_AGGRESSIVE" else "NORMAL", ("market_quality", "validation", "liquidity"))
    if structural.direction == "BEARISH" and tactical.action in {"SELL", "SHORT", "SELL_RALLIES", "RANGE_TRADE"}: return CompatibilityResult("SELL", 0.0, "NORMAL", ("market_quality", "validation", "liquidity"))
    return CompatibilityResult("NO_TRADE" if structural.direction == "NEUTRAL" else "WAIT", -20.0, "LOW", ("validation",), ("Structural and tactical states do not align.",))
