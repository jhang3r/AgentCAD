"""JSON-RPC 2.0 response builder."""
import json
from typing import Any, Optional


class ResponseBuilder:
    """Build JSON-RPC 2.0 responses."""

    def success(
        self,
        request_id: Any,
        data: dict[str, Any],
        operation_type: Optional[str] = None,
        execution_time_ms: Optional[int] = None
    ) -> str:
        """Build success response.

        Args:
            request_id: Request identifier to echo back
            data: Result data
            operation_type: Operation type for metadata
            execution_time_ms: Execution time in milliseconds

        Returns:
            JSON-RPC success response as string
        """
        result = {"status": "success", "data": data}

        # Add metadata if provided
        if operation_type or execution_time_ms is not None:
            result["metadata"] = {}
            if operation_type:
                result["metadata"]["operation_type"] = operation_type
            if execution_time_ms is not None:
                result["metadata"]["execution_time_ms"] = execution_time_ms

        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }

        return json.dumps(response)

    def error(
        self,
        request_id: Any,
        error_code: str,
        message: str,
        data: Optional[dict[str, Any]] = None
    ) -> str:
        """Build error response.

        Args:
            request_id: Request identifier to echo back
            error_code: Machine-readable error code
            message: Human-readable error message
            data: Additional error data (optional)

        Returns:
            JSON-RPC error response as string
        """
        error_obj = {
            "code": error_code,
            "message": message
        }

        if data:
            error_obj["data"] = data

        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": error_obj
        }

        return json.dumps(response)

    def progress(
        self,
        request_id: Any,
        percent: int,
        stage: str,
        estimated_time_remaining_ms: Optional[int] = None
    ) -> str:
        """Build progress response for long-running operations.

        Args:
            request_id: Request identifier to echo back
            percent: Progress percentage (0-100)
            stage: Current operation stage
            estimated_time_remaining_ms: Estimated time remaining (optional)

        Returns:
            JSON-RPC progress response as string
        """
        result = {
            "status": "progress",
            "percent": percent,
            "stage": stage
        }

        if estimated_time_remaining_ms is not None:
            result["estimated_time_remaining_ms"] = estimated_time_remaining_ms

        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }

        return json.dumps(response)

    def format_ndjson(self, response: str) -> str:
        """Format response as NDJSON (newline-delimited JSON).

        Args:
            response: JSON response string

        Returns:
            Response with newline appended
        """
        return response + "\n"

    def send_success(
        self,
        request_id: Any,
        data: dict[str, Any],
        operation_type: Optional[str] = None,
        execution_time_ms: Optional[int] = None
    ) -> str:
        """Build and format success response as NDJSON.

        Args:
            request_id: Request identifier
            data: Result data
            operation_type: Operation type
            execution_time_ms: Execution time

        Returns:
            NDJSON-formatted success response
        """
        response = self.success(request_id, data, operation_type, execution_time_ms)
        return self.format_ndjson(response)

    def send_error(
        self,
        request_id: Any,
        error_code: str,
        message: str,
        data: Optional[dict[str, Any]] = None
    ) -> str:
        """Build and format error response as NDJSON.

        Args:
            request_id: Request identifier
            error_code: Error code
            message: Error message
            data: Additional error data

        Returns:
            NDJSON-formatted error response
        """
        response = self.error(request_id, error_code, message, data)
        return self.format_ndjson(response)

    def send_progress(
        self,
        request_id: Any,
        percent: int,
        stage: str,
        estimated_time_remaining_ms: Optional[int] = None
    ) -> str:
        """Build and format progress response as NDJSON.

        Args:
            request_id: Request identifier
            percent: Progress percentage
            stage: Current stage
            estimated_time_remaining_ms: Estimated time remaining

        Returns:
            NDJSON-formatted progress response
        """
        response = self.progress(request_id, percent, stage, estimated_time_remaining_ms)
        return self.format_ndjson(response)
