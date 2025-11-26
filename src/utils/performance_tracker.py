"""Performance tracking for operations."""
import time
from typing import Optional


class PerformanceTracker:
    """Track operation execution time and performance metrics."""

    def __init__(self):
        """Initialize performance tracker."""
        self._start_time: Optional[float] = None
        self._operation_name: Optional[str] = None

    def start(self, operation_name: str) -> None:
        """Start timing an operation.

        Args:
            operation_name: Name of operation being tracked
        """
        self._operation_name = operation_name
        self._start_time = time.perf_counter()

    def stop(self) -> int:
        """Stop timing and return elapsed time.

        Returns:
            Elapsed time in milliseconds

        Raises:
            RuntimeError: If timing was not started
        """
        if self._start_time is None:
            raise RuntimeError("Performance tracking not started")

        elapsed_seconds = time.perf_counter() - self._start_time
        elapsed_ms = int(elapsed_seconds * 1000)

        self._start_time = None
        self._operation_name = None

        return elapsed_ms

    def get_elapsed_ms(self) -> int:
        """Get current elapsed time without stopping.

        Returns:
            Elapsed time in milliseconds

        Raises:
            RuntimeError: If timing was not started
        """
        if self._start_time is None:
            raise RuntimeError("Performance tracking not started")

        elapsed_seconds = time.perf_counter() - self._start_time
        return int(elapsed_seconds * 1000)


def measure_time(func):
    """Decorator to measure function execution time.

    Returns elapsed time in milliseconds via modified return value.
    Function must return a dict; 'execution_time_ms' will be added.

    Args:
        func: Function to measure

    Returns:
        Decorated function
    """
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        if isinstance(result, dict):
            result['execution_time_ms'] = elapsed_ms
        return result

    return wrapper
