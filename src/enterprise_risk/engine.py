from dataclasses import dataclass
@dataclass(frozen=True)
class RiskAssessment:
    status: str; requested_quantity: int; approved_quantity: int; utilization: float; reasons: tuple[str,...]; policy_version: str = "1.0.0"
class EnterpriseRiskEngine:
    """Deterministic pre-trade capital gate; no order or broker interaction."""
    def assess(self, *, requested_quantity:int, unit_risk:float, capital:float, used_capital:float, max_utilization:float=.8) -> RiskAssessment:
        projected=used_capital+requested_quantity*unit_risk; limit=capital*max_utilization
        if capital<=0 or unit_risk<=0: return RiskAssessment("BLOCK",requested_quantity,0,0,("Capital and unit risk must be positive.",))
        approved=max(0,min(requested_quantity,int(max(0,limit-used_capital)//unit_risk)))
        utilization=projected/capital
        if approved==0: return RiskAssessment("BLOCK",requested_quantity,0,utilization,("Capital-utilization limit breached.",))
        if approved<requested_quantity: return RiskAssessment("RESIZE",requested_quantity,approved,(used_capital+approved*unit_risk)/capital,("Quantity resized to policy limit.",))
        return RiskAssessment("ALLOW",requested_quantity,approved,utilization,())
