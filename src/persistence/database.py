"""SQLite database schema and connection management."""
import sqlite3
from pathlib import Path
from typing import Optional


class Database:
    """SQLite database connection and schema management."""

    def __init__(self, db_path: str | Path):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        """Establish database connection with proper settings.

        Returns:
            SQLite connection object
        """
        if self.connection is None:
            self.connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,  # Allow multi-threaded access
                isolation_level="DEFERRED"
            )
            self.connection.row_factory = sqlite3.Row  # Enable dict-like row access
            self.connection.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
            self.connection.execute("PRAGMA journal_mode = WAL")  # Write-Ahead Logging for performance
        return self.connection

    def initialize_schema(self) -> None:
        """Create all database tables if they don't exist."""
        conn = self.connect()
        cursor = conn.cursor()

        # Workspaces table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workspaces (
                workspace_id TEXT PRIMARY KEY,
                workspace_name TEXT NOT NULL UNIQUE,
                workspace_type TEXT NOT NULL CHECK (workspace_type IN ('main', 'agent_branch')),
                base_workspace_id TEXT,
                owning_agent_id TEXT,
                created_at TEXT NOT NULL,
                entity_count INTEGER DEFAULT 0,
                operation_count INTEGER DEFAULT 0,
                branch_status TEXT NOT NULL CHECK (branch_status IN ('clean', 'modified', 'conflicted', 'merged')),
                divergence_point TEXT,
                FOREIGN KEY (base_workspace_id) REFERENCES workspaces(workspace_id)
            )
        """)

        # Entities table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                entity_id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                modified_at TEXT NOT NULL,
                created_by_agent TEXT NOT NULL,
                parent_entities TEXT,  -- JSON array of entity IDs
                child_entities TEXT,   -- JSON array of entity IDs
                properties TEXT NOT NULL,  -- JSON object with entity-specific properties
                bounding_box TEXT NOT NULL,  -- JSON object {min: [x,y,z], max: [x,y,z]}
                is_valid INTEGER NOT NULL DEFAULT 1,
                validation_errors TEXT,  -- JSON array of error codes
                FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id)
            )
        """)

        # Constraints table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS constraints (
                constraint_id TEXT PRIMARY KEY,
                constraint_type TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                constrained_entities TEXT NOT NULL,  -- JSON array of 1-2 entity IDs
                parameters TEXT,  -- JSON object with constraint-specific parameters
                satisfaction_status TEXT NOT NULL CHECK (satisfaction_status IN ('satisfied', 'violated', 'redundant')),
                degrees_of_freedom_removed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                created_by_agent TEXT NOT NULL,
                FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id)
            )
        """)

        # Entity-Constraint junction table (many-to-many)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entity_constraints (
                entity_id TEXT NOT NULL,
                constraint_id TEXT NOT NULL,
                PRIMARY KEY (entity_id, constraint_id),
                FOREIGN KEY (entity_id) REFERENCES entities(entity_id) ON DELETE CASCADE,
                FOREIGN KEY (constraint_id) REFERENCES constraints(constraint_id) ON DELETE CASCADE
            )
        """)

        # Operations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS operations (
                operation_id TEXT PRIMARY KEY,
                operation_type TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                input_parameters TEXT NOT NULL,  -- JSON object
                input_entities TEXT,  -- JSON array of entity IDs
                output_entities TEXT,  -- JSON array of entity IDs
                result_status TEXT NOT NULL CHECK (result_status IN ('success', 'error', 'warning')),
                error_code TEXT,
                error_message TEXT,
                execution_time_ms INTEGER NOT NULL,
                undo_data TEXT,  -- JSON object with undo information
                FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id)
            )
        """)

        # Validation results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS validation_results (
                validation_id TEXT PRIMARY KEY,
                validation_type TEXT NOT NULL CHECK (validation_type IN ('topology', 'geometry', 'constraints')),
                checked_entities TEXT NOT NULL,  -- JSON array of entity IDs
                timestamp TEXT NOT NULL,
                overall_status TEXT NOT NULL CHECK (overall_status IN ('pass', 'fail', 'warning')),
                issues TEXT NOT NULL  -- JSON array of issue objects
            )
        """)

        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_workspace ON entities(workspace_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_agent ON entities(created_by_agent)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_constraints_workspace ON constraints(workspace_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_constraints_status ON constraints(satisfaction_status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_operations_workspace ON operations(workspace_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_operations_timestamp ON operations(workspace_id, timestamp)")

        conn.commit()

    def close(self) -> None:
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None

    def __enter__(self):
        """Context manager entry."""
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.connection:
            if exc_type is None:
                self.connection.commit()
            else:
                self.connection.rollback()
            self.close()
