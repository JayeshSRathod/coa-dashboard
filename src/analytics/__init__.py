"""Deterministic, research-only performance analytics for CQRP."""

from .engine import PerformanceAnalyticsEngine
from .models import AnalyticsReport, CompletedTrade, PerformanceSnapshot

__all__ = ["AnalyticsReport", "CompletedTrade", "PerformanceAnalyticsEngine", "PerformanceSnapshot"]
