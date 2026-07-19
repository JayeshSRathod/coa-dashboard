from dataclasses import dataclass
@dataclass(frozen=True)
class RiskConfig:
    risk_version:str="1.0.0"; sizing_method:str="FIXED_QUANTITY"; fixed_quantity:int=1
    fixed_capital:float=50000.; fixed_risk:float=2000.; portfolio_percent:float=.02
    max_risk_per_trade:float=5000.; max_portfolio_risk:float=20000.; max_daily_loss:float=3000.
    max_open_positions:int=3; max_instrument_exposure:float=100000.; cash_reserve_percent:float=.1
    def __post_init__(self):
        if self.sizing_method not in {"FIXED_QUANTITY","FIXED_CAPITAL","FIXED_RISK","PERCENT_PORTFOLIO","VOLATILITY_BASED"}:raise ValueError("unsupported sizing method")
        if self.fixed_quantity<1 or not 0<=self.cash_reserve_percent<1:raise ValueError("invalid risk configuration")
