import unittest

from src.eoc.alerts import AlertManager
from src.eoc.diagnostics import DiagnosticsCenter
from src.eoc.health import HealthMonitor, classify_health
from src.eoc.models import AlertSeverity, AuditEvent, ConfigurationRecord, HealthState, SchedulerRun
from src.eoc.notifications import NotificationRouter
from src.eoc.service import EnterpriseOperationsCenter
from src.persistence.connection import connect
from src.persistence.eoc_repository import (AlertRepository, AuditRepository,
    ConfigurationGovernanceRepository, DiagnosticsRepository, HealthRepository,
    MetricsRepository, NotificationRepository, SchedulerRepository)
from src.persistence.migration import apply_migrations
from src.persistence.schema import RESEARCH_MIGRATIONS


class Logger:
    def info(self, _message):
        pass


class EOCTests(unittest.TestCase):
    def setUp(self):
        connection = connect(":memory:")
        apply_migrations(connection, RESEARCH_MIGRATIONS)
        self.health = HealthRepository(connection)
        self.alerts = AlertRepository(connection)
        self.audit = AuditRepository(connection)
        self.scheduler = SchedulerRepository(connection)
        self.metrics = MetricsRepository(connection)
        self.notifications = NotificationRepository(connection)
        self.configurations = ConfigurationGovernanceRepository(connection)
        self.diagnostics = DiagnosticsRepository(connection)
        logger = Logger()
        router = NotificationRouter(self.notifications, logger, channels={"desktop": lambda alert: None})
        self.monitor = HealthMonitor(self.health, logger)
        self.alert_manager = AlertManager(self.alerts, logger, router)
        self.center = EnterpriseOperationsCenter(
            health_repository=self.health, alert_repository=self.alerts, audit_repository=self.audit,
            scheduler_repository=self.scheduler, metrics_repository=self.metrics,
            notification_repository=self.notifications, configuration_repository=self.configurations,
            diagnostics_repository=self.diagnostics, health_monitor=self.monitor,
            alert_manager=self.alert_manager,
            diagnostics_center=DiagnosticsCenter(self.diagnostics, logger, {
                "database": lambda: {"status": "HEALTHY", "recommendation": "No action required."}
            }),
        )

    def test_health_aggregation_and_states(self):
        self.assertEqual(classify_health(response_time_ms=20, error_count=0,
                         heartbeat_age_seconds=0, queue_backlog=0), HealthState.HEALTHY)
        self.monitor.publish(component="database", version="1", response_time_ms=800)
        summary = self.center.get_system_health()
        self.assertEqual(summary["components"][0]["status"], "WARNING")
        self.assertEqual(summary["summary"]["states"]["WARNING"], 1)

    def test_alert_deduplication_and_disabled_notifications(self):
        first = self.alert_manager.raise_alert(category="Database", severity=AlertSeverity.ERROR,
            component="database", message="connection lost", deduplication_key="db-lost")
        second = self.alert_manager.raise_alert(category="Database", severity="ERROR",
            component="database", message="connection lost", deduplication_key="db-lost")
        self.assertEqual(first.alert_id, second.alert_id)
        self.assertEqual(len(self.center.get_alerts()), 1)
        rows = self.notifications.connection.execute("SELECT status FROM eoc_notification_deliveries").fetchall()
        self.assertEqual(rows[0]["status"], "SKIPPED")

    def test_scheduler_audit_configuration_and_timeline(self):
        self.center.record_scheduler_observation(job_id="daily_scan", status="SUCCESS", result={"records": 2})
        self.center.record_audit_event(actor="user", action="CREATED", entity_type="Experiment", entity_id="exp-1")
        first = self.center.record_configuration(configuration_name="eoc", version="1", values={"enabled": True}, actor="user")
        second = self.center.record_configuration(configuration_name="eoc", version="1", values={"enabled": True}, actor="user")
        self.assertEqual(first.configuration_event_id, second.configuration_event_id)
        self.assertEqual(self.center.get_scheduler_status()[0]["job_id"], "daily_scan")
        self.assertEqual(self.center.get_audit_log()[0]["action"], "CREATED")
        self.assertEqual(len(self.center.get_configuration_history()), 1)
        self.assertEqual(self.center.get_activity_timeline()[0]["activity_type"], "AUDIT")

    def test_diagnostics_and_append_only_records(self):
        reports = self.center.run_diagnostics("corr-1")
        self.assertEqual(reports[0]["status"], "HEALTHY")
        event = AuditEvent.new(actor="user", action="VIEWED", entity_type="EOC", entity_id="dashboard")
        self.audit.append(event)
        with self.assertRaises(Exception):
            self.audit.connection.execute("DELETE FROM eoc_audit_events WHERE audit_id=?", (event.audit_id,))


if __name__ == "__main__":
    unittest.main()
