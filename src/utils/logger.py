"""Structured logging utilities."""
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Optional


class StructuredLogger:
    """Logger with structured JSON output."""

    def __init__(self, name: str, level: int = logging.INFO):
        """Initialize structured logger.

        Args:
            name: Logger name
            level: Logging level
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Remove existing handlers
        self.logger.handlers = []

        # Add JSON formatter to stderr
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(JSONFormatter())
        self.logger.addHandler(handler)

    def log_operation(
        self,
        operation_type: str,
        workspace_id: str,
        agent_id: str,
        status: str,
        execution_time_ms: int,
        **extra_data
    ) -> None:
        """Log an operation with structured data.

        Args:
            operation_type: Type of operation
            workspace_id: Workspace identifier
            agent_id: Agent identifier
            status: Operation status (success/error/warning)
            execution_time_ms: Execution time in milliseconds
            **extra_data: Additional operation-specific data
        """
        self.logger.info(
            "operation",
            extra={
                "operation_type": operation_type,
                "workspace_id": workspace_id,
                "agent_id": agent_id,
                "status": status,
                "execution_time_ms": execution_time_ms,
                **extra_data
            }
        )

    def log_error(
        self,
        error_code: str,
        error_message: str,
        **context
    ) -> None:
        """Log an error with context.

        Args:
            error_code: Error code
            error_message: Error message
            **context: Error context data
        """
        self.logger.error(
            error_message,
            extra={
                "error_code": error_code,
                **context
            }
        )

    def info(self, message: str, **extra: Any) -> None:
        """Log info message.

        Args:
            message: Log message
            **extra: Additional data
        """
        self.logger.info(message, extra=extra)

    def warning(self, message: str, **extra: Any) -> None:
        """Log warning message.

        Args:
            message: Log message
            **extra: Additional data
        """
        self.logger.warning(message, extra=extra)

    def error(self, message: str, **extra: Any) -> None:
        """Log error message.

        Args:
            message: Log message
            **extra: Additional data
        """
        self.logger.error(message, extra=extra)


class JSONFormatter(logging.Formatter):
    """Format log records as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record

        Returns:
            JSON-formatted log string
        """
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage()
        }

        # Add extra fields if present
        if hasattr(record, "__dict__"):
            for key, value in record.__dict__.items():
                if key not in ("name", "msg", "args", "created", "filename", "funcName",
                              "levelname", "levelno", "lineno", "module", "msecs",
                              "message", "pathname", "process", "processName",
                              "relativeCreated", "thread", "threadName", "exc_info",
                              "exc_text", "stack_info"):
                    log_data[key] = value

        return json.dumps(log_data)


# Global logger instance
_logger: Optional[StructuredLogger] = None


def get_logger(name: str = "cad_agent") -> StructuredLogger:
    """Get or create global logger instance.

    Args:
        name: Logger name

    Returns:
        StructuredLogger instance
    """
    global _logger
    if _logger is None:
        _logger = StructuredLogger(name)
    return _logger
