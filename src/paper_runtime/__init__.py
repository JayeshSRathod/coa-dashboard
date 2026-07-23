"""PAPER-only runtime coordination over CQRP's event-sourced execution engine."""

from .service import PaperRuntimeService, PaperRuntimeStatus

__all__ = ["PaperRuntimeService", "PaperRuntimeStatus"]
