"""Versioned COA research-engine boundary."""

from .adapter import FrozenCOAAdapter, SnapshotTranslationError
from .contracts import AnalysisEngine
from .models import COAResearchResult

__all__ = ["AnalysisEngine", "COAResearchResult", "FrozenCOAAdapter", "SnapshotTranslationError"]
