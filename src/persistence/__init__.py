"""Persistence boundaries for CQRP research data."""

from .connection import connect
from .migration import apply_migrations
from .research_repository import ResearchRepository
from .coa_result_repository import COAResultRepository
from .validation_repository import ValidationRepository
from .signal_repository import SignalRepository
from .trade_repository import TradeRepository
from .trade_event_repository import TradeEventRepository
from .portfolio_repository import PortfolioRepository
from .risk_decision_repository import RiskDecisionRepository
from .exposure_repository import ExposureRepository
from .analytics_repository import AnalyticsRepository
from .report_repository import ReportRepository
from .performance_snapshot_repository import PerformanceSnapshotRepository
from .order_repository import OrderRepository
from .order_event_repository import OrderEventRepository
from .broker_sync_repository import BrokerSyncRepository
from .execution_repository import ExecutionRepository
from .broker_repository import BrokerRepository
from .broker_account_repository import BrokerAccountRepository
from .instrument_repository import InstrumentRepository
from .execution_route_repository import ExecutionRouteRepository
from .market_provider_repository import MarketProviderRepository
from .strategy_repository import StrategyRepository
from .configuration_repository import ConfigurationRepository
from .dataset_repository import DatasetRepository
from .experiment_repository import ExperimentRepository
from .promotion_repository import PromotionRepository
from .research_notebook_repository import ResearchNotebookRepository
from .schema import RESEARCH_MIGRATIONS
from .snapshot_repository import SnapshotRepository


def initialize_research_database(database_path: str) -> ResearchRepository:
    """Open a CQRP research database and bring its schema to the latest version."""
    connection = connect(database_path)
    apply_migrations(connection, RESEARCH_MIGRATIONS)
    return ResearchRepository(connection)


def initialize_strategy_repository(database_path: str) -> StrategyRepository:
    connection = connect(database_path); apply_migrations(connection, RESEARCH_MIGRATIONS); return StrategyRepository(connection)


def initialize_configuration_repository(database_path: str) -> ConfigurationRepository:
    connection = connect(database_path); apply_migrations(connection, RESEARCH_MIGRATIONS); return ConfigurationRepository(connection)


def initialize_dataset_repository(database_path: str) -> DatasetRepository:
    connection = connect(database_path); apply_migrations(connection, RESEARCH_MIGRATIONS); return DatasetRepository(connection)


def initialize_experiment_repository(database_path: str) -> ExperimentRepository:
    connection = connect(database_path); apply_migrations(connection, RESEARCH_MIGRATIONS); return ExperimentRepository(connection)


def initialize_promotion_repository(database_path: str) -> PromotionRepository:
    connection = connect(database_path); apply_migrations(connection, RESEARCH_MIGRATIONS); return PromotionRepository(connection)


def initialize_research_notebook_repository(database_path: str) -> ResearchNotebookRepository:
    connection = connect(database_path); apply_migrations(connection, RESEARCH_MIGRATIONS); return ResearchNotebookRepository(connection)


def initialize_broker_repository(database_path: str) -> BrokerRepository:
    connection = connect(database_path)
    apply_migrations(connection, RESEARCH_MIGRATIONS)
    return BrokerRepository(connection)


def initialize_broker_account_repository(database_path: str) -> BrokerAccountRepository:
    connection = connect(database_path)
    apply_migrations(connection, RESEARCH_MIGRATIONS)
    return BrokerAccountRepository(connection)


def initialize_instrument_repository(database_path: str) -> InstrumentRepository:
    connection = connect(database_path)
    apply_migrations(connection, RESEARCH_MIGRATIONS)
    return InstrumentRepository(connection)


def initialize_execution_route_repository(database_path: str) -> ExecutionRouteRepository:
    connection = connect(database_path)
    apply_migrations(connection, RESEARCH_MIGRATIONS)
    return ExecutionRouteRepository(connection)


def initialize_market_provider_repository(database_path: str) -> MarketProviderRepository:
    connection = connect(database_path)
    apply_migrations(connection, RESEARCH_MIGRATIONS)
    return MarketProviderRepository(connection)


def initialize_execution_repository(database_path: str) -> ExecutionRepository:
    connection = connect(database_path)
    apply_migrations(connection, RESEARCH_MIGRATIONS)
    return ExecutionRepository(OrderRepository(connection), OrderEventRepository(connection))


def initialize_order_repository(database_path: str) -> OrderRepository:
    connection = connect(database_path)
    apply_migrations(connection, RESEARCH_MIGRATIONS)
    return OrderRepository(connection)


def initialize_order_event_repository(database_path: str) -> OrderEventRepository:
    connection = connect(database_path)
    apply_migrations(connection, RESEARCH_MIGRATIONS)
    return OrderEventRepository(connection)


def initialize_broker_sync_repository(database_path: str) -> BrokerSyncRepository:
    connection = connect(database_path)
    apply_migrations(connection, RESEARCH_MIGRATIONS)
    return BrokerSyncRepository(connection)


def initialize_analytics_repository(database_path: str) -> AnalyticsRepository:
    connection = connect(database_path)
    apply_migrations(connection, RESEARCH_MIGRATIONS)
    return AnalyticsRepository(connection)


def initialize_report_repository(database_path: str) -> ReportRepository:
    connection = connect(database_path)
    apply_migrations(connection, RESEARCH_MIGRATIONS)
    return ReportRepository(connection)


def initialize_performance_snapshot_repository(database_path: str) -> PerformanceSnapshotRepository:
    connection = connect(database_path)
    apply_migrations(connection, RESEARCH_MIGRATIONS)
    return PerformanceSnapshotRepository(connection)


def initialize_portfolio_repository(database_path: str) -> PortfolioRepository:
    connection = connect(database_path); apply_migrations(connection, RESEARCH_MIGRATIONS); return PortfolioRepository(connection)


def initialize_risk_decision_repository(database_path: str) -> RiskDecisionRepository:
    connection = connect(database_path); apply_migrations(connection, RESEARCH_MIGRATIONS); return RiskDecisionRepository(connection)


def initialize_exposure_repository(database_path: str) -> ExposureRepository:
    connection = connect(database_path); apply_migrations(connection, RESEARCH_MIGRATIONS); return ExposureRepository(connection)


def initialize_trade_repository(database_path: str) -> TradeRepository:
    """Open a migrated CQRP database for paper-trade identities."""
    connection = connect(database_path)
    apply_migrations(connection, RESEARCH_MIGRATIONS)
    return TradeRepository(connection)


def initialize_trade_event_repository(database_path: str) -> TradeEventRepository:
    """Open a migrated CQRP database for immutable paper-trade events."""
    connection = connect(database_path)
    apply_migrations(connection, RESEARCH_MIGRATIONS)
    return TradeEventRepository(connection)


def initialize_signal_repository(database_path: str) -> SignalRepository:
    """Open a migrated CQRP database for immutable research signals."""
    connection = connect(database_path)
    apply_migrations(connection, RESEARCH_MIGRATIONS)
    return SignalRepository(connection)


def initialize_validation_repository(database_path: str) -> ValidationRepository:
    """Open a migrated CQRP database for append-only validation results."""
    connection = connect(database_path)
    apply_migrations(connection, RESEARCH_MIGRATIONS)
    return ValidationRepository(connection)


def initialize_coa_result_repository(database_path: str) -> COAResultRepository:
    """Open a migrated CQRP database for immutable COA research results."""
    connection = connect(database_path)
    apply_migrations(connection, RESEARCH_MIGRATIONS)
    return COAResultRepository(connection)


def initialize_snapshot_repository(database_path: str) -> SnapshotRepository:
    """Open a migrated CQRP database for snapshot capture and replay."""
    connection = connect(database_path)
    apply_migrations(connection, RESEARCH_MIGRATIONS)
    return SnapshotRepository(connection)


__all__ = [
    "AnalyticsRepository",
    "StrategyRepository",
    "ConfigurationRepository",
    "DatasetRepository",
    "ExperimentRepository",
    "PromotionRepository",
    "ResearchNotebookRepository",
    "BrokerRepository",
    "BrokerAccountRepository",
    "InstrumentRepository",
    "ExecutionRouteRepository",
    "MarketProviderRepository",
    "BrokerSyncRepository",
    "ExecutionRepository",
    "COAResultRepository",
    "SignalRepository",
    "ExposureRepository",
    "PortfolioRepository",
    "RiskDecisionRepository",
    "ReportRepository",
    "PerformanceSnapshotRepository",
    "OrderRepository",
    "OrderEventRepository",
    "TradeEventRepository",
    "TradeRepository",
    "ValidationRepository",
    "ResearchRepository",
    "RESEARCH_MIGRATIONS",
    "SnapshotRepository",
    "apply_migrations",
    "connect",
    "initialize_analytics_repository",
    "initialize_strategy_repository",
    "initialize_configuration_repository",
    "initialize_dataset_repository",
    "initialize_experiment_repository",
    "initialize_promotion_repository",
    "initialize_research_notebook_repository",
    "initialize_broker_repository",
    "initialize_broker_account_repository",
    "initialize_execution_route_repository",
    "initialize_instrument_repository",
    "initialize_market_provider_repository",
    "initialize_broker_sync_repository",
    "initialize_order_event_repository",
    "initialize_order_repository",
    "initialize_coa_result_repository",
    "initialize_performance_snapshot_repository",
    "initialize_report_repository",
    "initialize_research_database",
    "initialize_snapshot_repository",
    "initialize_signal_repository",
    "initialize_execution_repository",
    "initialize_exposure_repository",
    "initialize_portfolio_repository",
    "initialize_risk_decision_repository",
    "initialize_trade_event_repository",
    "initialize_trade_repository",
    "initialize_validation_repository",
]
