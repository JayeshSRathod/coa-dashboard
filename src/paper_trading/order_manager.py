from src.decision.models import TradeDecision
from .models import PaperOrder
class PaperOrderManager:
    """Creates simulated orders only; never imports or calls a broker adapter."""
    def create(self, decision: TradeDecision) -> PaperOrder:
        if decision.action not in {"BUY", "SELL"} or decision.quantity <= 0: return PaperOrder.new(decision_id=decision.decision_id, instrument_id=decision.instrument, side=decision.action, quantity=0, order_type="MARKET", limit_price=None, status="REJECTED")
        return PaperOrder.new(decision_id=decision.decision_id, instrument_id=decision.instrument, side=decision.action, quantity=decision.quantity, order_type="MARKET", limit_price=decision.entry, status="VALIDATED")
