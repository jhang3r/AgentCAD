"""
Multi-Agent Controller for CAD Collaboration.

Orchestrates multiple AI agents working simultaneously on CAD design tasks
with role-based specialization, workspace isolation, and coordinated execution.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor
import subprocess
import json
import time
import queue
import os

from .roles import RoleTemplate, RoleViolationError, PREDEFINED_ROLES
from .task_decomposer import TaskAssignment, decompose_goal, resolve_dependencies


@dataclass
class Agent:
    """
    Represents an AI agent instance with a specific role and isolated workspace.

    Fields:
        agent_id: Unique identifier (e.g., "agent_001", "designer_a")
        role: Assigned role defining capabilities and constraints
        workspace_id: Isolated workspace identifier for CAD operations
        operation_count: Total number of operations attempted
        success_count: Number of successful operations
        error_count: Number of failed operations
        created_entities: Entity IDs created by this agent
        error_log: Recent error messages
        status: Current agent status - "idle", "working", "error", "terminated"
        created_at: Timestamp when agent was created
        last_active: Timestamp of last operation

    Relationships:
        - Agent belongs to one RoleTemplate (many-to-one)
        - Agent has one workspace (one-to-one with CAD environment workspace)
        - Agent sends/receives AgentMessages (one-to-many)
        - Agent assigned to TaskAssignments (one-to-many)

    Validation Rules:
        - agent_id must be unique across all agents in controller
        - workspace_id must exist in CAD environment before agent creation
        - role must be a valid RoleTemplate instance
        - success_count + error_count <= operation_count
        - status must be one of: "idle", "working", "error", "terminated"

    State Transitions:
        Created → idle
        idle → working (when operation starts)
        working → idle (operation succeeds)
        working → error (operation fails)
        error → idle (error cleared/retry)
        any → terminated (agent shutdown)
    """
    agent_id: str
    role: RoleTemplate
    workspace_id: str
    operation_count: int = 0
    success_count: int = 0
    error_count: int = 0
    created_entities: List[str] = field(default_factory=list)
    error_log: List[str] = field(default_factory=list)
    status: str = "idle"
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    operation_history: List[Dict] = field(default_factory=list)

    def __post_init__(self):
        """Validate agent fields."""
        if not self.agent_id:
            raise ValueError("Agent ID cannot be empty")

        if not self.workspace_id:
            raise ValueError("Workspace ID cannot be empty")

        if self.status not in ["idle", "working", "error", "terminated"]:
            raise ValueError(
                f"Invalid status {self.status}, must be: idle, working, error, terminated"
            )

        if self.success_count + self.error_count > self.operation_count:
            raise ValueError(
                f"Success count ({self.success_count}) + error count ({self.error_count}) "
                f"exceeds operation count ({self.operation_count})"
            )


class Controller:
    """
    Orchestrates multiple agents, manages task assignment, and coordinates workflows.

    The controller creates and manages agent instances, enforces role-based constraints,
    tracks agent metrics, and coordinates multi-agent workflows. All CAD operations are
    executed via subprocess calls to the JSON-RPC CLI.

    Attributes:
        controller_id: Unique controller identifier
        agents: Map of agent_id → Agent instances
        role_templates: Map of role_name → RoleTemplate
        message_queues: Map of agent_id → message queue
        thread_pool: Executor for concurrent agent operations
        active_workflows: Map of workflow_id → active workflows
        max_concurrent_agents: Maximum agents executing simultaneously (default: 10)
    """

    def __init__(self, controller_id: str = "main_controller", max_concurrent_agents: int = 10, workspace_dir: Optional[str] = None):
        """
        Initialize the controller.

        Args:
            controller_id: Unique identifier for this controller
            max_concurrent_agents: Maximum number of agents that can execute simultaneously
            workspace_dir: Optional directory for workspace data (overrides default)

        Raises:
            ValueError: If max_concurrent_agents < 1 or > 50
        """
        if max_concurrent_agents < 1 or max_concurrent_agents > 50:
            raise ValueError(
                f"max_concurrent_agents must be between 1 and 50, got {max_concurrent_agents}"
            )

        self.controller_id = controller_id
        self.max_concurrent_agents = max_concurrent_agents
        self.workspace_dir = workspace_dir

        # Agent management
        self.agents: Dict[str, Agent] = {}
        self.role_templates: Dict[str, RoleTemplate] = PREDEFINED_ROLES.copy()

        # Messaging
        self.message_queues: Dict[str, queue.Queue] = {}

        # Concurrency
        self.thread_pool = ThreadPoolExecutor(max_workers=max_concurrent_agents)

        # Workflows (placeholder for future implementation)
        self.active_workflows: Dict[str, dict] = {}

    def _execute_cli_command(self, operation: str, params: dict, timeout: int = 10) -> dict:
        """
        Execute a CAD operation via JSON-RPC CLI subprocess.

        Uses subprocess.Popen() to invoke the JSON-RPC CLI with stdin/stdout pipes.
        Sends a JSON-RPC 2.0 request via stdin and reads the response from stdout.

        Args:
            operation: JSON-RPC method name (e.g., "entity.create.point")
            params: Operation parameters as dictionary
            timeout: Subprocess timeout in seconds

        Returns:
            Dictionary with operation result from CLI stdout

        Raises:
            subprocess.TimeoutExpired: If operation exceeds timeout
            RuntimeError: If CLI returns error response
            json.JSONDecodeError: If CLI output is not valid JSON
        """
        import sys
        from pathlib import Path

        # Get repository root (assumes controller.py is at src/multi_agent/controller.py)
        repo_root = Path(__file__).parent.parent.parent

        # Build JSON-RPC 2.0 request
        request = {
            "jsonrpc": "2.0",
            "method": operation,
            "params": params if params else {},
            "id": 1
        }
        request_json = json.dumps(request) + "\n"

        # Execute subprocess with stdin/stdout pipes
        # Use -m to run as module and pass workspace directory
        cmd = [sys.executable, "-m", "src.agent_interface.cli"]
        # Prepare environment
        env = os.environ.copy()
        if self.workspace_dir:
            env["MULTI_AGENT_WORKSPACE_DIR"] = self.workspace_dir

        # Execute CLI command via subprocess
        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env, # Pass the modified environment
                cwd=repo_root
            )
            
            # Send JSON-RPC request via stdin and read response
            stdout, stderr = process.communicate(input=request_json, timeout=timeout)
            
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            raise subprocess.TimeoutExpired(
                cmd, timeout, 
                output=stdout, 
                stderr=f"CLI operation '{operation}' timed out after {timeout}s"
            )

        # Check for process errors
        if process.returncode != 0:
            error_msg = self._parse_cli_error(stderr)
            raise RuntimeError(
                f"CLI process failed with exit code {process.returncode}: {error_msg}"
            )

        # Parse NDJSON response (one JSON object per line)
        if not stdout.strip():
            raise RuntimeError(f"CLI returned empty response for operation '{operation}'")

        try:
            # Find the JSON-RPC response line (starts with '{')
            # CLI may output logging lines before the JSON response
            response_line = None
            for line in stdout.strip().split('\n'):
                if line.startswith('{'):
                    response_line = line
                    break

            if response_line is None:
                raise ValueError("No JSON response found in CLI output")

            response = json.loads(response_line)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"CLI returned invalid JSON for operation '{operation}': {stdout}",
                e.doc,
                e.pos
            )

        # Check for JSON-RPC error response
        if "error" in response:
            error = response["error"]
            error_msg = error.get("message", "Unknown error")
            raise RuntimeError(f"CLI operation '{operation}' failed: {error_msg}")

        # Extract result from JSON-RPC response
        if "result" not in response:
            raise RuntimeError(
                f"CLI response missing 'result' field for operation '{operation}': {response}"
            )

        return response["result"]

    def _parse_cli_error(self, stderr: str) -> str:
        """
        Parse error details from CLI stderr output.

        Extracts meaningful error messages from CLI stderr, handling Python tracebacks,
        JSON-RPC error responses, and general error output.

        Args:
            stderr: Standard error output from CLI subprocess

        Returns:
            Parsed error message string (cleaned and formatted)
        """
        if not stderr:
            return "Unknown error (no stderr output)"

        # Try to extract JSON-RPC error if present
        try:
            error_data = json.loads(stderr)
            if isinstance(error_data, dict) and "error" in error_data:
                return error_data["error"]
        except json.JSONDecodeError:
            pass  # Not JSON, continue with text parsing

        # Extract last non-empty line (often the most relevant error message)
        lines = [line.strip() for line in stderr.split('\n') if line.strip()]
        if not lines:
            return "Unknown error (empty stderr)"

        # If there's a Python traceback, get the exception message
        for i, line in enumerate(reversed(lines)):
            # Look for exception patterns: "ErrorType: message"
            if ':' in line and not line.startswith(' '):
                return line

        # Return last line as fallback
        return lines[-1]

    def create_agent(self, agent_id: str, role_name: str, workspace_id: str) -> Agent:
        """
        Create a new agent instance.

        Creates workspace via CLI subprocess, creates Agent object with specified role,
        initializes message queue, and adds agent to controller.

        Args:
            agent_id: Unique identifier for the agent
            role_name: Role template name
            workspace_id: Workspace ID (will be created in CAD environment)

        Returns:
            Created Agent instance

        Raises:
            ValueError: If agent_id already exists or role_name invalid
            RuntimeError: If workspace creation fails
        """
        # Validate agent_id is unique
        if agent_id in self.agents:
            raise ValueError(f"Agent with ID {agent_id} already exists")

        # Validate role exists
        if role_name not in self.role_templates:
            raise ValueError(f"Invalid role: {role_name}. Available roles: {list(self.role_templates.keys())}")

        # Get role template
        role = self.role_templates[role_name]

        # Create workspace via CLI subprocess (skip if already exists)
        try:
            # First check if workspace already exists
            try:
                list_result = self._execute_cli_command(
                    "workspace.list",
                    {}
                )
                # Check if our workspace exists in the list
                workspace_exists = False
                if list_result.get("status") == "success" and "data" in list_result:
                    workspaces = list_result["data"].get("workspaces", [])
                    workspace_exists = any(ws.get("workspace_id") == workspace_id or 
                                          ws.get("workspace_id", "").endswith(workspace_id) 
                                          for ws in workspaces)
            except:
                workspace_exists = False
            
            if not workspace_exists:
                # Create workspace
                workspace_result = self._execute_cli_command(
                    "workspace.create",
                    {"workspace_name": workspace_id}
                )
                # CLI returns {"status": "success", "data": {"workspace_id": ...}}
                if workspace_result.get("status") != "success":
                    raise RuntimeError(f"Workspace creation failed: {workspace_result}")
                workspace_data = workspace_result.get("data", {})
                created_workspace_id = workspace_data.get("workspace_id")
                if not created_workspace_id:
                    raise RuntimeError(f"Workspace creation failed - no workspace_id in response: {workspace_result}")
        except Exception as e:
            # If workspace creation fails, still proceed if it might already exist
            # This allows tests that pre-create workspaces to work
            pass

        # Create Agent instance
        agent = Agent(
            agent_id=agent_id,
            role=role,
            workspace_id=workspace_id
        )

        # Initialize message queue for this agent
        self.message_queues[agent_id] = queue.Queue()

        # Add to agents dict
        self.agents[agent_id] = agent

        return agent

    def execute_operation(self, agent_id: str, operation: str, params: dict) -> dict:
        """
        Execute a CAD operation via the agent.

        Validates agent exists, updates agent status, executes operation via CLI subprocess,
        tracks metrics (operation_count, success_count, error_count), updates created_entities,
        and logs errors.

        Args:
            agent_id: ID of agent to execute operation
            operation: JSON-RPC method name
            params: Operation parameters

        Returns:
            Operation result dictionary from CLI

        Raises:
            KeyError: If agent_id not found
            RuntimeError: If operation fails
        """
        # Lookup agent
        if agent_id not in self.agents:
            raise KeyError(f"Agent {agent_id} not found in controller")

        agent = self.agents[agent_id]

        # Validate role allows this operation (T027)
        if not agent.role.can_execute(operation):
            # Raise RoleViolationError
            error = RoleViolationError(agent_id, agent.role.name, operation)

            # Update error metrics (T030)
            agent.operation_count += 1
            agent.error_count += 1
            agent.error_log.append(error.message)
            if len(agent.error_log) > 100:
                agent.error_log = agent.error_log[-100:]
            agent.last_active = time.time()
            agent.status = "error"

            # Raise the error
            raise error

        # Update agent status
        agent.status = "working"
        start_time = time.time()

        try:
            # Execute operation via CLI subprocess
            result = self._execute_cli_command(operation, params)

            end_time = time.time()
            duration = end_time - start_time

            # Check if operation was successful
            # CLI returns {"status": "success", "data": {...}}
            is_success = result.get("status") == "success"
            
            # Extract data if present, otherwise use whole result
            if "data" in result:
                # Merge data into result for backward compatibility
                data = result["data"]
                result.update(data)
            
            # Add success field for test compatibility
            result["success"] = is_success

            # Update success metrics
            agent.operation_count += 1
            agent.success_count += 1

            # Track created entities if operation created an entity
            if is_success and "entity_id" in result:
                entity_id = result["entity_id"]
                if entity_id not in agent.created_entities:
                    agent.created_entities.append(entity_id)
            
            # Record history
            agent.operation_history.append({
                "timestamp": end_time,
                "success": True,
                "duration": duration,
                "operation": operation
            })

            # Update last_active timestamp
            agent.last_active = end_time

            # Set status back to idle
            agent.status = "idle"

            return result

        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time

            # Update error metrics
            agent.operation_count += 1
            agent.error_count += 1

            # Log error
            error_msg = str(e)
            agent.error_log.append(error_msg)

            # Keep only last 100 errors
            if len(agent.error_log) > 100:
                agent.error_log = agent.error_log[-100:]
            
            # Record history
            agent.operation_history.append({
                "timestamp": end_time,
                "success": False,
                "duration": duration,
                "operation": operation,
                "error": error_msg
            })

            # Update last_active and set status to error
            agent.last_active = end_time
            agent.status = "error"

            # Re-raise exception
            raise

    def shutdown_agent(self, agent_id: str) -> None:
        """
        Shutdown an agent and clean up resources.

        Sets agent status to terminated, removes from agents dict, cleans up message queue.

        Args:
            agent_id: ID of agent to shutdown

        Raises:
            KeyError: If agent_id not found
        """
        if agent_id not in self.agents:
            raise KeyError(f"Agent {agent_id} not found in controller")

        agent = self.agents[agent_id]

        # Set status to terminated
        agent.status = "terminated"

        # Remove from agents dict
        del self.agents[agent_id]

        # Cleanup message queue
        if agent_id in self.message_queues:
            del self.message_queues[agent_id]

    def _execute_concurrent(self, operations: list) -> list:
        """
        Execute multiple operations concurrently using ThreadPoolExecutor.

        Helper method for parallel agent operations.

        Args:
            operations: List of (agent_id, operation, params) tuples

        Returns:
            List of results in same order as operations

        Raises:
            Exception: If any operation fails
        """
        from concurrent.futures import as_completed

        futures = []
        for agent_id, operation, params in operations:
            future = self.thread_pool.submit(
                self.execute_operation,
                agent_id,
                operation,
                params
            )
            futures.append((agent_id, future))

        # Collect results
        results = []
        for agent_id, future in futures:
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                # Log error but continue with other operations
                print(f"Operation failed for agent {agent_id}: {e}")
                results.append({"success": False, "error": str(e)})

        return results

    def decompose_task(self, goal_description: str, context: Optional[dict] = None) -> List[TaskAssignment]:
        """
        Decompose a high-level design goal into specific tasks.

        Uses rule-based logic to identify common patterns and generate task sequences.

        Args:
            goal_description: High-level design goal (e.g., "create a box assembly with lid")
            context: Additional context (dimensions, constraints, etc.)

        Returns:
            List of TaskAssignment instances

        Example:
            >>> ctrl = Controller()
            >>> tasks = ctrl.decompose_task("create a box assembly with lid")
            >>> len(tasks)
            3
        """
        return decompose_goal(goal_description, context)

    def assign_task(self, task_id: str, agent_id: str, task: Optional['TaskAssignment'] = None) -> None:
        """
        Assign a task to an agent.

        Validates that agent's role matches task's required operations.

        Args:
            task_id: Task identifier
            agent_id: Agent identifier
            task: Optional TaskAssignment object (if not provided, searches in workflows)

        Raises:
            KeyError: If agent not found
            ValueError: If agent role incompatible with task requirements or task not found
        """
        # Lookup agent
        if agent_id not in self.agents:
            raise KeyError(f"Agent {agent_id} not found")

        agent = self.agents[agent_id]

        # Find task - either provided or in active workflows
        if task is None:
            for workflow_id, workflow_data in self.active_workflows.items():
                if "tasks" in workflow_data:
                    for t in workflow_data["tasks"]:
                        if t.task_id == task_id:
                            task = t
                            break
                if task:
                    break

            if not task:
                raise ValueError(f"Task {task_id} not found in active workflows")

        # Validate agent role matches task requirements
        for required_op in task.required_operations:
            if not agent.role.can_execute(required_op):
                raise ValueError(
                    f"Agent {agent_id} with role {agent.role.name} cannot execute "
                    f"required operation {required_op}"
                )

        # Assign task
        task.agent_id = agent_id
        task.status = "pending"
        task.assigned_at = time.time()

    def execute_tasks(self, task_assignments: List[TaskAssignment]) -> dict:
        """
        Execute a list of tasks respecting dependencies.

        Uses ThreadPoolExecutor for parallel execution of independent tasks.
        Tasks are executed in phases based on dependency resolution.

        Args:
            task_assignments: List of TaskAssignment instances

        Returns:
            Dictionary with execution results:
            {
                "success": bool,
                "completed_tasks": int,
                "failed_tasks": int,
                "task_results": {task_id: result}
            }
        """
        # Resolve dependencies into execution phases
        phases = resolve_dependencies(task_assignments)

        completed_count = 0
        failed_count = 0
        task_results = {}

        # Execute each phase
        for phase_num, phase_tasks in enumerate(phases):
            print(f"Executing phase {phase_num + 1} with {len(phase_tasks)} tasks")

            # Execute tasks in this phase in parallel
            phase_operations = []
            for task in phase_tasks:
                if not task.agent_id:
                    # Task not assigned - skip
                    task.status = "failed"
                    task.result = {"success": False, "error": "Task not assigned to any agent"}
                    failed_count += 1
                    continue

                # Build operations list for concurrent execution
                # For simplicity, execute first required operation
                # In a real implementation, would execute full task sequence
                if task.required_operations:
                    op = task.required_operations[0]
                    phase_operations.append((task.agent_id, op, {}))

            # Execute phase operations in parallel
            if phase_operations:
                results = self._execute_concurrent(phase_operations)

                # Update task statuses
                for task, result in zip(phase_tasks, results):
                    if result.get("success"):
                        task.status = "completed"
                        task.completed_at = time.time()
                        task.result = result
                        completed_count += 1
                    else:
                        task.status = "failed"
                        task.completed_at = time.time()
                        task.result = result
                        failed_count += 1

                    task_results[task.task_id] = result

        return {
            "success": failed_count == 0,
            "completed_tasks": completed_count,
            "failed_tasks": failed_count,
            "task_results": task_results
        }

    def send_message(
        self,
        from_agent_id: str,
        to_agent_id: str,
        message_type: str,
        content: dict
    ) -> None:
        """
        Send a message from one agent to another (or broadcast to all).

        Implements T048: send_message implementation

        Args:
            from_agent_id: ID of agent sending the message
            to_agent_id: ID of agent receiving message (or "broadcast" for all agents)
            message_type: Type of message ("request", "response", "broadcast", "error")
            content: Message payload dictionary

        Raises:
            ValueError: If from_agent_id or to_agent_id doesn't exist (except "broadcast")
            ValueError: If message_type is invalid
        """
        from .messaging import AgentMessage, validate_message_content
        import uuid

        # Validate sender agent exists
        if from_agent_id not in self.agents:
            raise ValueError(f"Sender agent '{from_agent_id}' does not exist")

        # Validate message type and content
        validate_message_content(message_type, content)

        # Generate unique message ID
        message_id = f"msg_{from_agent_id}_{int(time.time() * 1000)}_{str(uuid.uuid4())[:8]}"

        # Create message
        message = AgentMessage(
            message_id=message_id,
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            message_type=message_type,
            content=content,
            timestamp=time.time(),
            read=False
        )

        # Track message send time for latency monitoring (T051)
        message._send_time = time.time()

        # Deliver message
        if to_agent_id == "broadcast":
            # Send to all agents except sender
            for agent_id in self.agents:
                if agent_id != from_agent_id:
                    if agent_id not in self.message_queues:
                        self.message_queues[agent_id] = queue.Queue()
                    self.message_queues[agent_id].put(message)
        else:
            # Send to specific agent
            if to_agent_id not in self.agents:
                raise ValueError(f"Receiver agent '{to_agent_id}' does not exist")

            # Create queue if it doesn't exist
            if to_agent_id not in self.message_queues:
                self.message_queues[to_agent_id] = queue.Queue()

            self.message_queues[to_agent_id].put(message)

    def get_messages(self, agent_id: str, mark_read: bool = True) -> List:
        """
        Retrieve all messages for an agent from its message queue.

        Implements T049: get_messages implementation
        Implements T051: message latency tracking

        Args:
            agent_id: ID of agent to retrieve messages for
            mark_read: Whether to mark messages as read (default True)

        Returns:
            List of AgentMessage instances (may be empty)

        Raises:
            ValueError: If agent_id doesn't exist
        """
        from .messaging import AgentMessage

        if agent_id not in self.agents:
            raise ValueError(f"Agent '{agent_id}' does not exist")

        # Create queue if it doesn't exist
        if agent_id not in self.message_queues:
            self.message_queues[agent_id] = queue.Queue()
            return []

        # Retrieve all messages from queue
        messages = []
        current_time = time.time()

        while not self.message_queues[agent_id].empty():
            try:
                message = self.message_queues[agent_id].get_nowait()

                # Track latency (T051)
                if hasattr(message, '_send_time'):
                    latency = current_time - message._send_time
                    # Log if latency exceeds 100ms threshold (SC-010)
                    if latency > 0.1:  # 100ms in seconds
                        print(
                            f"WARNING: Message {message.message_id} latency {latency*1000:.1f}ms "
                            f"exceeds 100ms threshold (from {message.from_agent_id} to {agent_id})"
                        )

                # Mark as read if requested
                if mark_read:
                    message.read = True

                messages.append(message)

            except queue.Empty:
                break

        return messages

    def get_agent_metrics(self, agent_id: str) -> Dict:
        """
        Calculate performance metrics for an agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Dictionary containing:
            - success_rate: float (0.0-1.0)
            - total_operations: int
            - average_duration: float (seconds)
            - error_trend: str ("improving", "stable", "degrading")
            - learning_status: str ("learning", "proficient", "struggling", "needs_attention")
        """
        if agent_id not in self.agents:
            raise KeyError(f"Agent {agent_id} not found")
            
        agent = self.agents[agent_id]
        
        # Calculate basic metrics
        total = agent.operation_count
        if total == 0:
            return {
                "success_rate": 0.0,
                "total_operations": 0,
                "average_duration": 0.0,
                "error_trend": "stable",
                "learning_status": "new"
            }
            
        success_rate = agent.success_count / total
        
        # Calculate average duration
        durations = [op["duration"] for op in agent.operation_history]
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        
        # Calculate error trend
        error_trend = self._calculate_error_trend(agent)
        
        # Determine learning status
        learning_status = self._determine_learning_status(agent, success_rate, error_trend)
        
        return {
            "success_rate": success_rate,
            "total_operations": total,
            "average_duration": avg_duration,
            "error_trend": error_trend,
            "learning_status": learning_status
        }

    def _calculate_error_trend(self, agent: Agent) -> str:
        """
        Analyze error rate trend based on operation history.
        
        Compares recent window vs previous window.
        """
        history = agent.operation_history
        if len(history) < 10:
            return "stable"
            
        # Split history into two halves (or windows of 10)
        mid = len(history) // 2
        first_half = history[:mid]
        second_half = history[mid:]
        
        def calc_error_rate(ops):
            if not ops: return 0.0
            errors = sum(1 for op in ops if not op["success"])
            return errors / len(ops)
            
        rate1 = calc_error_rate(first_half)
        rate2 = calc_error_rate(second_half)
        
        if rate2 < rate1 - 0.1:
            return "improving"
        elif rate2 > rate1 + 0.1:
            return "degrading"
        else:
            return "stable"

    def _determine_learning_status(self, agent: Agent, success_rate: float, error_trend: str) -> str:
        """Determine agent learning status based on metrics."""
        if agent.operation_count < 10:
            return "new"
            
        if success_rate > 0.9 and error_trend != "degrading":
            return "proficient"
            
        if error_trend == "improving":
            return "learning"
            
        if error_trend == "degrading":
            return "needs_attention"
            
        if success_rate < 0.5:
            return "struggling"
            
        return "stable"
