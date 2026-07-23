from dataclasses import dataclass
from src.decision.models import TradeDecision
from .execution_modes import ExecutionMode
@dataclass(frozen=True)
class ExecutionApproval: decision_id: str; approved: bool; mode: ExecutionMode; reason: str
class ExecutionApprovalEngine:
    """Hard gate: Auto is rejected; Assisted needs explicit operator approval and a healthy system."""
    def evaluate(self, decision: TradeDecision, mode: ExecutionMode, *, operator_approved: bool=False, system_healthy: bool=False, kill_switch: bool=True) -> ExecutionApproval:
        if kill_switch: return ExecutionApproval(decision.decision_id, False, mode, "Kill switch is active.")
        if decision.action not in {"BUY","SELL"} or decision.quantity <= 0: return ExecutionApproval(decision.decision_id, False, mode, "Decision is not executable.")
        if mode is ExecutionMode.AUTO: return ExecutionApproval(decision.decision_id, False, mode, "Auto execution is disabled by default.")
        if mode is ExecutionMode.ASSISTED and operator_approved and system_healthy: return ExecutionApproval(decision.decision_id, True, mode, "Explicit assisted approval accepted.")
        return ExecutionApproval(decision.decision_id, False, mode, "Only a healthy, explicitly approved Assisted order may proceed.")
