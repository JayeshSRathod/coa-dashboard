"""Persistence boundaries for CQRP research data."""

from .connection import connect
from .migration import apply_migrations
from .research_repository import ResearchRepository
from .coa_result_repository import COAResultRepository
from .schema import RESEARCH_MIGRATIONS
from .snapshot_repository import SnapshotRepository


def initialize_research_database(database_path: str) -> ResearchRepository:
    """Open a CQRP research database and bring its schema to the latest version."""
    connection = connect(database_path)
    apply_migrations(connection, RESEARCH_MIGRATIONS)
    return ResearchRepository(connection)


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
    "COAResultRepository",
    "ResearchRepository",
    "RESEARCH_MIGRATIONS",
    "SnapshotRepository",
    "apply_migrations",
    "connect",
    "initialize_coa_result_repository",
    "initialize_research_database",
    "initialize_snapshot_repository",
]
