"""Small, dependency-free settings boundary for CQRP services."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    environment: str
    data_dir: Path
    database_path: Path
    log_dir: Path
    snapshot_interval_seconds: float

    @classmethod
    def from_environment(cls, project_root: Path | None = None) -> "Settings":
        root = project_root or Path(__file__).resolve().parents[2]
        data_dir = Path(os.getenv("CQRP_DATA_DIR", root / "data"))
        interval = float(os.getenv("CQRP_SNAPSHOT_INTERVAL_SECONDS", "3"))
        if interval <= 0:
            raise ValueError("CQRP_SNAPSHOT_INTERVAL_SECONDS must be positive")
        return cls(
            environment=os.getenv("CQRP_ENV", "development"),
            data_dir=data_dir,
            database_path=Path(os.getenv("CQRP_DATABASE_PATH", data_dir / "cqrp.db")),
            log_dir=Path(os.getenv("CQRP_LOG_DIR", root / "logs")),
            snapshot_interval_seconds=interval,
        )
