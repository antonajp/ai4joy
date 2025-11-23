"""Structured logging for Cloud Logging integration"""
import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional


class CloudLogger:
    """
    Structured logger for GCP Cloud Logging with JSON formatting.
    Logs are compatible with Chrome DevTools console and Cloud Logging.
    """

    def __init__(self, name: str, level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))

        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(self._get_formatter())
            self.logger.addHandler(handler)

    def _get_formatter(self) -> logging.Formatter:
        """Get JSON formatter for structured logging"""
        return logging.Formatter(
            '{"severity": "%(levelname)s", "timestamp": "%(asctime)s", '
            '"logger": "%(name)s", "message": "%(message)s"}'
        )

    def _log_structured(self, level: str, message: str, **kwargs):
        """Log structured data with optional context fields"""
        log_entry = {
            "severity": level,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "message": message,
        }

        if kwargs:
            log_entry.update(kwargs)

        getattr(self.logger, level.lower())(json.dumps(log_entry))

    def info(self, message: str, **kwargs):
        """Log info message with optional context"""
        self._log_structured("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message with optional context"""
        self._log_structured("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message with optional context"""
        self._log_structured("ERROR", message, **kwargs)

    def debug(self, message: str, **kwargs):
        """Log debug message with optional context"""
        self._log_structured("DEBUG", message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message with optional context"""
        self._log_structured("CRITICAL", message, **kwargs)


def get_logger(name: str, level: str = "INFO") -> CloudLogger:
    """Get or create logger instance"""
    return CloudLogger(name, level)
