"""Alerting service for monitoring thresholds and anomalies"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from app.config import get_settings
from app.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels"""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class Alert:
    """Alert data structure"""

    severity: AlertSeverity
    metric: str
    message: str
    current_value: float
    threshold: float
    timestamp: datetime
    metadata: Optional[Dict] = None


class AlertingService:
    """
    Service for monitoring thresholds and generating alerts.

    Monitors:
    - P95 latency against threshold (default 8s)
    - Error rate against threshold (default 5%)
    - Cache hit rate (alert if <50%)
    """

    def __init__(
        self,
        latency_threshold: float = None,
        error_rate_threshold: float = None,
        cache_hit_rate_threshold: float = None,
    ):
        self.latency_threshold = latency_threshold or settings.alert_latency_threshold
        self.error_rate_threshold = (
            error_rate_threshold or settings.alert_error_rate_threshold
        )
        self.cache_hit_rate_threshold = (
            cache_hit_rate_threshold or settings.alert_cache_hit_rate_threshold
        )

        self.alerts: List[Alert] = []

        logger.info(
            "Alerting service initialized",
            latency_threshold=self.latency_threshold,
            error_rate_threshold=self.error_rate_threshold,
            cache_hit_rate_threshold=self.cache_hit_rate_threshold,
        )

    def check_latency(
        self, p95_latency: float, metric_name: str = "turn_latency"
    ) -> Optional[Alert]:
        """
        Check p95 latency against threshold.

        Args:
            p95_latency: 95th percentile latency in seconds
            metric_name: Name of the metric being checked

        Returns:
            Alert if threshold exceeded, None otherwise
        """
        if p95_latency > self.latency_threshold:
            severity = (
                AlertSeverity.CRITICAL
                if p95_latency > self.latency_threshold * 1.5
                else AlertSeverity.WARNING
            )

            alert = Alert(
                severity=severity,
                metric=f"{metric_name}_p95",
                message=f"High latency detected: {p95_latency:.2f}s exceeds threshold {self.latency_threshold}s",
                current_value=p95_latency,
                threshold=self.latency_threshold,
                timestamp=datetime.now(timezone.utc),
                metadata={"metric_name": metric_name},
            )

            self._record_alert(alert)
            return alert

        return None

    def check_error_rate(
        self, total_requests: int, error_count: int
    ) -> Optional[Alert]:
        """
        Check error rate against threshold.

        Args:
            total_requests: Total number of requests
            error_count: Number of errors

        Returns:
            Alert if threshold exceeded, None otherwise
        """
        if total_requests == 0:
            return None

        error_rate = error_count / total_requests

        if error_rate > self.error_rate_threshold:
            severity = (
                AlertSeverity.CRITICAL
                if error_rate > self.error_rate_threshold * 2
                else AlertSeverity.WARNING
            )

            alert = Alert(
                severity=severity,
                metric="error_rate",
                message=f"High error rate detected: {error_rate:.2%} exceeds threshold {self.error_rate_threshold:.2%}",
                current_value=error_rate,
                threshold=self.error_rate_threshold,
                timestamp=datetime.now(timezone.utc),
                metadata={"total_requests": total_requests, "error_count": error_count},
            )

            self._record_alert(alert)
            return alert

        return None

    def check_cache_hit_rate(
        self, cache_hits: int, cache_total: int
    ) -> Optional[Alert]:
        """
        Check cache hit rate against threshold.

        Args:
            cache_hits: Number of cache hits
            cache_total: Total cache operations

        Returns:
            Alert if below threshold, None otherwise
        """
        if cache_total == 0:
            return None

        hit_rate = cache_hits / cache_total

        if hit_rate < self.cache_hit_rate_threshold:
            severity = (
                AlertSeverity.WARNING
                if hit_rate > self.cache_hit_rate_threshold * 0.5
                else AlertSeverity.CRITICAL
            )

            alert = Alert(
                severity=severity,
                metric="cache_hit_rate",
                message=f"Low cache hit rate detected: {hit_rate:.2%} below threshold {self.cache_hit_rate_threshold:.2%}",
                current_value=hit_rate,
                threshold=self.cache_hit_rate_threshold,
                timestamp=datetime.now(timezone.utc),
                metadata={"cache_hits": cache_hits, "cache_total": cache_total},
            )

            self._record_alert(alert)
            return alert

        return None

    def _record_alert(self, alert: Alert):
        """Record alert and log it"""
        self.alerts.append(alert)

        log_method = {
            AlertSeverity.INFO: logger.info,
            AlertSeverity.WARNING: logger.warning,
            AlertSeverity.CRITICAL: logger.critical,
        }[alert.severity]

        log_method(
            f"ALERT: {alert.message}",
            severity=alert.severity.value,
            metric=alert.metric,
            current_value=alert.current_value,
            threshold=alert.threshold,
            metadata=alert.metadata,
        )

    def get_recent_alerts(self, count: int = 10) -> List[Alert]:
        """Get most recent alerts"""
        return self.alerts[-count:] if self.alerts else []

    def get_alerts_by_severity(self, severity: AlertSeverity) -> List[Alert]:
        """Get all alerts of a specific severity"""
        return [alert for alert in self.alerts if alert.severity == severity]

    def clear_alerts(self):
        """Clear all alerts"""
        self.alerts.clear()
        logger.info("Alerts cleared")

    def get_alert_summary(self) -> Dict[str, int]:
        """Get summary of alerts by severity"""
        summary = {
            "total": len(self.alerts),
            "info": len(self.get_alerts_by_severity(AlertSeverity.INFO)),
            "warning": len(self.get_alerts_by_severity(AlertSeverity.WARNING)),
            "critical": len(self.get_alerts_by_severity(AlertSeverity.CRITICAL)),
        }

        return summary


_alerting_service: Optional[AlertingService] = None


def get_alerting_service() -> AlertingService:
    """Get or create singleton alerting service instance"""
    global _alerting_service
    if _alerting_service is None:
        _alerting_service = AlertingService()
    return _alerting_service
