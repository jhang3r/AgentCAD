"""Agent learning metrics tracking.

Tracks agent performance over time to measure learning progress.
Critical metrics:
- Total operations
- Success rate (overall)
- Error rate in first 10 operations vs last 10 operations
- Error reduction percentage (learning indicator)
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class OperationRecord:
    """Record of a single operation."""
    timestamp: str
    operation_type: str
    success: bool
    error_code: int = 0
    error_message: str = ""


@dataclass
class AgentMetrics:
    """Agent learning metrics.

    Tracks performance over time to measure learning progress.
    """
    agent_id: str
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    operation_history: list[OperationRecord] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Overall success rate."""
        if self.total_operations == 0:
            return 0.0
        return self.successful_operations / self.total_operations

    @property
    def error_rate(self) -> float:
        """Overall error rate."""
        return 1.0 - self.success_rate

    @property
    def error_rate_first_10(self) -> float:
        """Error rate in first 10 operations."""
        first_10 = self.operation_history[:10]
        if len(first_10) == 0:
            return 0.0
        errors = sum(1 for op in first_10 if not op.success)
        return errors / len(first_10)

    @property
    def error_rate_last_10(self) -> float:
        """Error rate in last 10 operations."""
        last_10 = self.operation_history[-10:]
        if len(last_10) == 0:
            return 0.0
        errors = sum(1 for op in last_10 if not op.success)
        return errors / len(last_10)

    @property
    def error_reduction_percentage(self) -> float:
        """Percentage reduction in errors (learning indicator).

        Positive value means agent is learning (fewer errors over time).
        Negative value means agent is getting worse.
        """
        if self.total_operations < 20:
            # Not enough data to measure learning
            return 0.0

        first_rate = self.error_rate_first_10
        last_rate = self.error_rate_last_10

        if first_rate == 0:
            # Started perfect, can't improve
            return 0.0

        reduction = (first_rate - last_rate) / first_rate * 100
        return reduction

    @property
    def is_learning(self) -> bool:
        """Check if agent is learning (error rate decreasing)."""
        return self.error_reduction_percentage > 0

    def record_operation(self, operation_type: str, success: bool,
                        error_code: int = 0, error_message: str = "") -> None:
        """Record an operation result.

        Args:
            operation_type: Type of operation performed
            success: Whether operation succeeded
            error_code: Error code if failed
            error_message: Error message if failed
        """
        self.total_operations += 1

        if success:
            self.successful_operations += 1
        else:
            self.failed_operations += 1

        record = OperationRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            operation_type=operation_type,
            success=success,
            error_code=error_code,
            error_message=error_message
        )

        self.operation_history.append(record)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            "agent_id": self.agent_id,
            "total_operations": self.total_operations,
            "successful_operations": self.successful_operations,
            "failed_operations": self.failed_operations,
            "success_rate": round(self.success_rate, 4),
            "error_rate": round(self.error_rate, 4),
            "error_rate_first_10": round(self.error_rate_first_10, 4),
            "error_rate_last_10": round(self.error_rate_last_10, 4),
            "error_reduction_percentage": round(self.error_reduction_percentage, 2),
            "is_learning": self.is_learning,
            "learning_status": self._get_learning_status()
        }

    def _get_learning_status(self) -> str:
        """Get human-readable learning status."""
        if self.total_operations < 20:
            return "insufficient_data"

        reduction = self.error_reduction_percentage

        if reduction > 50:
            return "excellent_learning"
        elif reduction > 25:
            return "good_learning"
        elif reduction > 0:
            return "slight_improvement"
        elif reduction == 0:
            return "stable"
        elif reduction > -25:
            return "slight_regression"
        else:
            return "significant_regression"


class MetricsTracker:
    """Tracks metrics for multiple agents."""

    def __init__(self):
        """Initialize metrics tracker."""
        self.agents: dict[str, AgentMetrics] = {}

    def get_agent_metrics(self, agent_id: str) -> AgentMetrics:
        """Get or create metrics for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            AgentMetrics instance
        """
        if agent_id not in self.agents:
            self.agents[agent_id] = AgentMetrics(agent_id=agent_id)
        return self.agents[agent_id]

    def record_operation(self, agent_id: str, operation_type: str,
                        success: bool, error_code: int = 0,
                        error_message: str = "") -> None:
        """Record an operation for an agent.

        Args:
            agent_id: Agent identifier
            operation_type: Type of operation
            success: Whether operation succeeded
            error_code: Error code if failed
            error_message: Error message if failed
        """
        metrics = self.get_agent_metrics(agent_id)
        metrics.record_operation(operation_type, success, error_code, error_message)
