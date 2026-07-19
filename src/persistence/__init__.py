"""Persistence boundaries for CQRP research data."""

from .connection import connect
from .migration import apply_migrations
from .research_repository import ResearchRepository
from .schema import RESEARCH_MIGRATIONS


def initialize_research_database(database_path: str) -> ResearchRepository:
    """Open a CQRP research database and bring its schema to the latest version."""
    connection = connect(database_path)
    apply_migrations(connection, RESEARCH_MIGRATIONS)
    return ResearchRepository(connection)


__all__ = [
    "ResearchRepository",
    "RESEARCH_MIGRATIONS",
    "apply_migrations",
    "connect",
    "initialize_research_database",
]
