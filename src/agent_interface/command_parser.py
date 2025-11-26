"""JSON-RPC 2.0 request parser for agent commands."""
import json
from typing import Any, Optional


class JSONRPCRequest:
    """Parsed JSON-RPC 2.0 request.

    Attributes:
        jsonrpc: Protocol version (must be "2.0")
        method: Method name to invoke
        params: Method parameters (dict or list)
        id: Request identifier (number or string)
    """

    def __init__(
        self,
        jsonrpc: str,
        method: str,
        params: Any,
        request_id: Any
    ):
        """Initialize request.

        Args:
            jsonrpc: Protocol version
            method: Method name
            params: Method parameters
            request_id: Request identifier
        """
        self.jsonrpc = jsonrpc
        self.method = method
        self.params = params if params is not None else {}
        self.id = request_id

    def __repr__(self) -> str:
        """String representation."""
        return f"JSONRPCRequest(method={self.method}, id={self.id})"


class CommandParser:
    """Parse JSON-RPC 2.0 requests from agent input."""

    def parse(self, json_string: str) -> tuple[Optional[JSONRPCRequest], Optional[dict[str, Any]]]:
        """Parse JSON-RPC request from string.

        Args:
            json_string: Raw JSON-RPC request string

        Returns:
            Tuple of (parsed_request, error_response)
            If parsing succeeds: (JSONRPCRequest, None)
            If parsing fails: (None, error_response_dict)
        """
        # Try to parse JSON
        try:
            data = json.loads(json_string)
        except json.JSONDecodeError as e:
            return None, {
                "jsonrpc": "2.0",
                "error": {
                    "code": "PARSE_ERROR",
                    "message": f"Invalid JSON: {str(e)}"
                },
                "id": None
            }

        # Validate JSON-RPC structure
        error = self._validate_request(data)
        if error:
            return None, error

        # Extract fields
        request = JSONRPCRequest(
            jsonrpc=data["jsonrpc"],
            method=data["method"],
            params=data.get("params"),
            request_id=data.get("id")
        )

        return request, None

    def _validate_request(self, data: Any) -> Optional[dict[str, Any]]:
        """Validate JSON-RPC request structure.

        Args:
            data: Parsed JSON data

        Returns:
            Error response dict if invalid, None if valid
        """
        request_id = data.get("id")

        # Must be an object
        if not isinstance(data, dict):
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "Request must be a JSON object"
                },
                "id": request_id
            }

        # Check jsonrpc version
        if "jsonrpc" not in data:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "Missing 'jsonrpc' field"
                },
                "id": request_id
            }

        if data["jsonrpc"] != "2.0":
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": f"Invalid jsonrpc version: {data['jsonrpc']} (must be '2.0')"
                },
                "id": request_id
            }

        # Check method
        if "method" not in data:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "Missing 'method' field"
                },
                "id": request_id
            }

        if not isinstance(data["method"], str):
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "Method must be a string"
                },
                "id": request_id
            }

        # Check params (optional, but must be object or array if present)
        if "params" in data:
            params = data["params"]
            if not isinstance(params, (dict, list)):
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": "INVALID_REQUEST",
                        "message": "Params must be an object or array"
                    },
                    "id": request_id
                }

        return None

    def get_param(
        self,
        request: JSONRPCRequest,
        param_name: str,
        required: bool = False,
        default: Any = None
    ) -> Any:
        """Extract parameter from request.

        Args:
            request: Parsed JSON-RPC request
            param_name: Parameter name to extract
            required: Whether parameter is required
            default: Default value if not present

        Returns:
            Parameter value

        Raises:
            KeyError: If required parameter is missing
        """
        if isinstance(request.params, dict):
            if required and param_name not in request.params:
                raise KeyError(f"Missing required parameter: {param_name}")
            return request.params.get(param_name, default)
        else:
            # Positional parameters not supported in this implementation
            raise ValueError("Positional parameters not supported")
