"""Read-only diagnostic runner for CQRP operations."""

from __future__ import annotations

from .models import DiagnosticReport


class DiagnosticsCenter:
    """Runs injected, side-effect-free probes and records their evidence."""

    def __init__(self, repository, logger, probes: dict[str, object] | None = None) -> None:
        self.repository = repository
        self.logger = logger
        self.probes = dict(probes or {})

    def run(self, correlation_id: str | None = None) -> list[DiagnosticReport]:
        reports: list[DiagnosticReport] = []
        for name, probe in sorted(self.probes.items()):
            try:
                result = dict(probe())
                status = str(result.get("status", "HEALTHY"))
                recommendation = str(result.get("recommendation", "No action required."))
                details = dict(result.get("details", {}))
            except Exception as exc:  # probes must never disrupt CQRP
                status, recommendation = "FAILED", "Inspect the diagnostic probe and its dependencies."
                details = {"error_type": type(exc).__name__}
            report = DiagnosticReport.new(name=name, status=status,
                                          recommendation=recommendation, details=details,
                                          correlation_id=correlation_id)
            reports.append(self.repository.append(report))
            self.logger.info({"event": "eoc_diagnostic_completed", "diagnostic": name,
                              "status": status, "correlation_id": correlation_id})
        return reports
