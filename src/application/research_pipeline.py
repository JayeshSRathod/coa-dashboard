"""CQRP shadow-research composition root for Sprints 203 and 204.

This module wires repositories, deterministic engines, services, and read-only
API facades around one SQLite connection. It deliberately exposes no live-order
adapter and therefore cannot place, modify, or cancel broker orders.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from src.api.paper_trade_lifecycle import PaperTradeLifecycleApiV1
from src.api.premarket_validation import PreMarketValidationApiV1
from src.execution.lifecycle_service import PaperTradeLifecycleService
from src.persistence.premarket_validation_repository import PreMarketValidationRepository
from src.persistence.trade_event_repository import TradeEventRepository
from src.persistence.trade_repository import TradeRepository
from src.premarket_validation.service import PreMarketValidationService


@dataclass(frozen=True)
class ShadowResearchPipeline:
    premarket_validation: PreMarketValidationService
    paper_lifecycle: PaperTradeLifecycleService
    premarket_api: PreMarketValidationApiV1
    lifecycle_api: PaperTradeLifecycleApiV1
    mode: str = "SHADOW_PAPER_ONLY"


def build_shadow_research_pipeline(connection: sqlite3.Connection) -> ShadowResearchPipeline:
    """Build the complete Sprint-203/204 service graph around ``connection``."""
    connection.row_factory = sqlite3.Row
    validation_repository = PreMarketValidationRepository(connection)
    trade_repository = TradeRepository(connection)
    event_repository = TradeEventRepository(connection)

    validation_service = PreMarketValidationService(validation_repository)
    lifecycle_service = PaperTradeLifecycleService(trade_repository, event_repository)

    return ShadowResearchPipeline(
        premarket_validation=validation_service,
        paper_lifecycle=lifecycle_service,
        premarket_api=PreMarketValidationApiV1(validation_service),
        lifecycle_api=PaperTradeLifecycleApiV1(lifecycle_service),
    )
