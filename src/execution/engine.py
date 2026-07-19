"""Deterministic event producer for simulated option trades; no broker calls."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.signal.models import ResearchSignal

from .config import PaperExecutionConfig
from .costs import apply_slippage, transaction_cost
from .fills import option_quote
from .models import PaperTrade, TradeEvent, TradeState


def _spot_range(snapshot: Mapping[str, Any]) -> tuple[float, float, float]:
    spot=float(snapshot["spot"])
    metadata=snapshot.get("metadata") or {}
    low=float(metadata.get("spot_low", spot)) if isinstance(metadata,Mapping) else spot
    high=float(metadata.get("spot_high", spot)) if isinstance(metadata,Mapping) else spot
    return spot,low,high


class PaperExecutionEngine:
    created_by="PaperExecutionEngine"

    def __init__(self, config: PaperExecutionConfig | None=None)->None:
        self.config=config or PaperExecutionConfig()

    def create_trade(self, signal: ResearchSignal, snapshot: Mapping[str,Any], *, experiment_id: str|None=None)->tuple[PaperTrade|None,list[TradeEvent]]:
        if signal.signal_type not in {"BUY","SELL"}:
            return None,[]
        quantity=(self.config.default_quantity//self.config.minimum_lot_size)*self.config.minimum_lot_size
        if quantity<self.config.minimum_lot_size:return None,[]
        strike=snapshot.get("atm_strike")
        if strike is None:
            chain=snapshot.get("option_chain") or []
            if chain and isinstance(chain[0],Mapping):strike=chain[0].get("Strike")
        option_type="CE" if signal.direction=="BUY" else "PE"
        entry=signal.entry_price
        span=abs((signal.target_2 or entry or 0)-(entry or 0))
        stop=(entry-span*self.config.stop_loss_range_fraction if signal.direction=="BUY" and entry is not None
              else entry+span*self.config.stop_loss_range_fraction if entry is not None else None)
        trade=PaperTrade.new(signal_id=signal.signal_id,session_id=signal.session_id,snapshot_id=signal.snapshot_id,
          experiment_id=experiment_id,strategy_version=signal.strategy_version,execution_version=self.config.execution_version,
          instrument=signal.instrument,direction=signal.direction,expiry=signal.expiry,strike=float(strike) if strike is not None else None,
          option_type=option_type,quantity=quantity,intended_entry=entry,initial_stop_loss=stop,
          initial_target_1=signal.target_1,initial_target_2=signal.target_2,initial_trailing_reference=None,created_by=self.created_by)
        timestamp=str(snapshot.get("market_captured_at") or snapshot.get("captured_at"))
        events=[
          TradeEvent.new(trade_id=trade.trade_id,session_id=trade.session_id,source_snapshot_id=trade.snapshot_id,event_type="TRADE_CREATED",occurred_at=timestamp,
              payload={"quantity":quantity,"stop_loss":stop,"target_1":signal.target_1,"target_2":signal.target_2,"trailing_reference":None},created_by=self.created_by),
          TradeEvent.new(trade_id=trade.trade_id,session_id=trade.session_id,source_snapshot_id=None,event_type="ENTRY_PENDING",occurred_at=timestamp,payload={},created_by=self.created_by),
          TradeEvent.new(trade_id=trade.trade_id,session_id=trade.session_id,source_snapshot_id=None,event_type="STOP_LOSS_SET",occurred_at=timestamp,payload={"stop_loss":stop},created_by=self.created_by),
          TradeEvent.new(trade_id=trade.trade_id,session_id=trade.session_id,source_snapshot_id=None,event_type="TARGET_1_SET",occurred_at=timestamp,payload={"target_1":signal.target_1},created_by=self.created_by),
          TradeEvent.new(trade_id=trade.trade_id,session_id=trade.session_id,source_snapshot_id=None,event_type="TARGET_2_SET",occurred_at=timestamp,payload={"target_2":signal.target_2},created_by=self.created_by)]
        return trade,events

    def _fill(self,trade,snapshot,is_entry):
        source=self.config.entry_price_source if is_entry else self.config.exit_price_source
        price=option_quote(snapshot,trade.strike,trade.option_type or "CE",source)
        return apply_slippage(price,is_entry=is_entry,config=self.config) if price is not None else None

    def _hit(self,trade,state,snapshot):
        _,low,high=_spot_range(snapshot)
        stop=(low<=state.stop_loss if trade.direction=="BUY" else high>=state.stop_loss) if state.stop_loss is not None else False
        t1=(high>=state.target_1 if trade.direction=="BUY" else low<=state.target_1) if state.target_1 is not None else False
        t2=(high>=state.target_2 if trade.direction=="BUY" else low<=state.target_2) if state.target_2 is not None else False
        if stop and (t1 or t2):
            return "STOP" if self.config.ambiguity_policy in {"CONSERVATIVE","STOP_FIRST"} else ("T2" if t2 else "T1")
        if stop:return "STOP"
        if t2:return "T2"
        if t1:return "T1"
        return None

    def _exit_event(self,trade,state,snapshot,quantity,event_type,reason):
        price=self._fill(trade,snapshot,False)
        if price is None:return None
        entry_cost=transaction_cost(state.executed_entry or price,quantity,self.config)
        cost=transaction_cost(price,quantity,self.config)
        delta=(price-(state.executed_entry or price))*quantity-cost-entry_cost
        return TradeEvent.new(trade_id=trade.trade_id,session_id=trade.session_id,source_snapshot_id=snapshot["snapshot_id"],
          event_type=event_type,occurred_at=snapshot["market_captured_at"],payload={"quantity":quantity,"price":price,"cost":cost,"realized_pnl_delta":delta,"reason":reason},created_by=self.created_by)

    def process_snapshot(self,trade:PaperTrade,state:TradeState,snapshot:Mapping[str,Any])->list[TradeEvent]:
        if state.status in {"CLOSED","CANCELLED","EXPIRED","REJECTED"}:return []
        if snapshot["snapshot_id"]==trade.snapshot_id:return []
        timestamp=snapshot["market_captured_at"]
        if state.status=="PENDING":
            should_fill=self.config.fill_policy=="NEXT_SNAPSHOT"
            if self.config.fill_policy=="CLOSE_CONFIRMATION" and trade.intended_entry is not None:
                spot,_,_= _spot_range(snapshot);should_fill=spot>=trade.intended_entry if trade.direction=="BUY" else spot<=trade.intended_entry
            if self.config.fill_policy=="TOUCH_PRICE" and trade.intended_entry is not None:
                _,low,high=_spot_range(snapshot);should_fill=low<=trade.intended_entry<=high
            if not should_fill:return []
            price=self._fill(trade,snapshot,True)
            if price is None:
                return [TradeEvent.new(trade_id=trade.trade_id,session_id=trade.session_id,source_snapshot_id=snapshot["snapshot_id"],event_type="ENTRY_REJECTED",occurred_at=timestamp,payload={"reason":"option quote unavailable"},created_by=self.created_by)]
            cost=transaction_cost(price,trade.quantity,self.config)
            return [TradeEvent.new(trade_id=trade.trade_id,session_id=trade.session_id,source_snapshot_id=snapshot["snapshot_id"],event_type="ENTRY_FILLED",occurred_at=timestamp,payload={"price":price,"quantity":trade.quantity,"cost":cost},created_by=self.created_by)]
        price=self._fill(trade,snapshot,False)
        events=[]
        if price is not None and state.executed_entry is not None:
            pnl=(price-state.executed_entry)*state.quantity_remaining
            events.append(TradeEvent.new(trade_id=trade.trade_id,session_id=trade.session_id,source_snapshot_id=snapshot["snapshot_id"],event_type="MARK_OBSERVED",occurred_at=timestamp,payload={"unrealized_pnl":pnl,"mfe":max(state.mfe,pnl),"mae":min(state.mae,pnl)},created_by=self.created_by))
        hit=self._hit(trade,state,snapshot)
        if hit=="STOP":
            event=self._exit_event(trade,state,snapshot,state.quantity_remaining,"EXIT_FILLED","STOP_LOSS")
            return events+([event] if event else [])
        if hit=="T2":
            events.append(TradeEvent.new(trade_id=trade.trade_id,session_id=trade.session_id,source_snapshot_id=snapshot["snapshot_id"],event_type="TARGET_2_HIT",occurred_at=timestamp,payload={},created_by=self.created_by))
            event=self._exit_event(trade,state,snapshot,state.quantity_remaining,"EXIT_FILLED","TARGET_2")
            return events+([event] if event else [])
        if hit=="T1" and state.status=="OPEN":
            events.append(TradeEvent.new(trade_id=trade.trade_id,session_id=trade.session_id,source_snapshot_id=snapshot["snapshot_id"],event_type="TARGET_1_HIT",occurred_at=timestamp,payload={},created_by=self.created_by))
            quantity=max(self.config.minimum_lot_size,int(trade.quantity*self.config.target_1_fraction)//self.config.minimum_lot_size*self.config.minimum_lot_size)
            quantity=min(quantity,state.quantity_remaining)
            event=self._exit_event(trade,state,snapshot,quantity,"PARTIAL_EXIT" if quantity<state.quantity_remaining else "EXIT_FILLED","TARGET_1")
            if event:events.append(event)
            if quantity<state.quantity_remaining and self.config.trailing_mode=="BREAKEVEN_AFTER_T1":
                events.append(TradeEvent.new(trade_id=trade.trade_id,session_id=trade.session_id,source_snapshot_id=None,event_type="STOP_LOSS_MOVED",occurred_at=timestamp,payload={"stop_loss":trade.intended_entry},created_by=self.created_by))
                events.append(TradeEvent.new(trade_id=trade.trade_id,session_id=trade.session_id,source_snapshot_id=None,event_type="TRAILING_UPDATED",occurred_at=timestamp,payload={"trailing_reference":trade.intended_entry},created_by=self.created_by))
        return events

    def force_close(self,trade,state,snapshot):
        if state.status not in {"OPEN","PARTIALLY_EXITED"}:return []
        event=self._exit_event(trade,state,snapshot,state.quantity_remaining,"EXIT_FILLED","SESSION_END")
        return [event] if event else []
