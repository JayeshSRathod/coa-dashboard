"""Central logging configuration for CQRP processes."""

from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(log_dir: Path, level: int = logging.INFO) -> None:
    """Configure idempotent file and console logging for a CQRP process."""
    log_dir.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger("cqrp")
    if root.handlers:
        return
    root.setLevel(level)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    file_handler = logging.FileHandler(log_dir / "application.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    root.addHandler(console)
    root.addHandler(file_handler)
