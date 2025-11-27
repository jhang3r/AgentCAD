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

        # Geometry kernel tables (003-geometry-kernel)

        # Geometry shapes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS geometry_shapes (
                shape_id TEXT PRIMARY KEY,
                shape_type TEXT NOT NULL,
                brep_data TEXT NOT NULL,
                is_valid BOOLEAN NOT NULL,
                created_at TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id)
            )
        """)

        # Solid properties table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS solid_properties (
                entity_id TEXT PRIMARY KEY,
                volume REAL NOT NULL,
                surface_area REAL NOT NULL,
                center_of_mass_x REAL NOT NULL,
                center_of_mass_y REAL NOT NULL,
                center_of_mass_z REAL NOT NULL,
                bounding_box_min_x REAL NOT NULL,
                bounding_box_min_y REAL NOT NULL,
                bounding_box_min_z REAL NOT NULL,
                bounding_box_max_x REAL NOT NULL,
                bounding_box_max_y REAL NOT NULL,
                bounding_box_max_z REAL NOT NULL,
                face_count INTEGER NOT NULL,
                edge_count INTEGER NOT NULL,
                vertex_count INTEGER NOT NULL,
                is_closed BOOLEAN NOT NULL,
                is_manifold BOOLEAN NOT NULL,
                computed_at TEXT NOT NULL,
                FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
            )
        """)

        # Creation operations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS creation_operations (
                operation_id TEXT PRIMARY KEY,
                operation_type TEXT NOT NULL,
                input_entity_ids TEXT NOT NULL,
                output_entity_id TEXT NOT NULL,
                parameters TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                executed_at TEXT NOT NULL,
                execution_time_ms INTEGER NOT NULL,
                success BOOLEAN NOT NULL,
                error_message TEXT,
                FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id),
                FOREIGN KEY (output_entity_id) REFERENCES entities(entity_id)
            )
        """)

        # Boolean operations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS boolean_operations (
                operation_id TEXT PRIMARY KEY,
                operation_type TEXT NOT NULL,
                operand1_entity_id TEXT NOT NULL,
                operand2_entity_id TEXT NOT NULL,
                output_entity_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                executed_at TEXT NOT NULL,
                execution_time_ms INTEGER NOT NULL,
                success BOOLEAN NOT NULL,
                error_message TEXT,
                FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id),
                FOREIGN KEY (operand1_entity_id) REFERENCES entities(entity_id),
                FOREIGN KEY (operand2_entity_id) REFERENCES entities(entity_id),
                FOREIGN KEY (output_entity_id) REFERENCES entities(entity_id)
            )
        """)

        # Tessellation configs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tessellation_configs (
                config_id TEXT PRIMARY KEY,
                linear_deflection REAL NOT NULL,
                angular_deflection REAL NOT NULL,
                relative BOOLEAN NOT NULL,
                is_default BOOLEAN NOT NULL
            )
        """)

        # Mesh data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mesh_data (
                mesh_id TEXT PRIMARY KEY,
                entity_id TEXT NOT NULL,
                triangle_count INTEGER NOT NULL,
                vertex_count INTEGER NOT NULL,
                tessellation_config_id TEXT NOT NULL,
                mesh_size_bytes INTEGER NOT NULL,
                generated_at TEXT NOT NULL,
                FOREIGN KEY (entity_id) REFERENCES entities(entity_id),
                FOREIGN KEY (tessellation_config_id) REFERENCES tessellation_configs(config_id)
            )
        """)

        # Add shape_id column to entities table if it doesn't exist
        # Check if column exists first
        cursor.execute("PRAGMA table_info(entities)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'shape_id' not in columns:
            cursor.execute("ALTER TABLE entities ADD COLUMN shape_id TEXT REFERENCES geometry_shapes(shape_id)")

        # Populate tessellation config presets
        cursor.execute("SELECT COUNT(*) FROM tessellation_configs")
        if cursor.fetchone()[0] == 0:
            # Insert three presets: preview, standard (default), high_quality
            cursor.execute("""
                INSERT INTO tessellation_configs
                (config_id, linear_deflection, angular_deflection, relative, is_default)
                VALUES
                ('preview', 1.0, 1.0, 0, 0),
                ('standard', 0.1, 0.5, 0, 1),
                ('high_quality', 0.01, 0.1, 0, 0)
            """)

        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_workspace ON entities(workspace_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_agent ON entities(created_by_agent)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_constraints_workspace ON constraints(workspace_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_constraints_status ON constraints(satisfaction_status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_operations_workspace ON operations(workspace_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_operations_timestamp ON operations(workspace_id, timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_geometry_shapes_workspace ON geometry_shapes(workspace_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_shape ON entities(shape_id)")

        conn.commit()

    def get_geometry_shape(self, shape_id: str):
        """Retrieve a geometry shape from the database.

        Args:
            shape_id: Shape ID to retrieve

        Returns:
            GeometryShape object or None if not found
        """
        from ..cad_kernel.geometry_engine import GeometryShape

        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT shape_id, shape_type, brep_data, is_valid, created_at, workspace_id
            FROM geometry_shapes
            WHERE shape_id = ?
        """, (shape_id,))

        row = cursor.fetchone()
        if row is None:
            return None

        return GeometryShape(
            shape_id=row[0],
            shape_type=row[1],
            brep_data=row[2],
            is_valid=bool(row[3]),
            created_at=row[4],
            workspace_id=row[5]
        )

    def save_geometry_shape(self, geo_shape) -> None:
        """Save a geometry shape to the database.

        Args:
            geo_shape: GeometryShape object to save
        """
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO geometry_shapes
            (shape_id, shape_type, brep_data, is_valid, created_at, workspace_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            geo_shape.shape_id,
            geo_shape.shape_type,
            geo_shape.brep_data,
            int(geo_shape.is_valid),
            geo_shape.created_at,
            geo_shape.workspace_id
        ))

    def save_solid_properties(self, entity_id: str, props) -> None:
        """Save solid properties to the database.

        Args:
            entity_id: Entity ID to associate properties with
            props: SolidProperties object
        """
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO solid_properties
            (entity_id, volume, surface_area, center_of_mass_x, center_of_mass_y, center_of_mass_z,
             bounding_box_min_x, bounding_box_min_y, bounding_box_min_z,
             bounding_box_max_x, bounding_box_max_y, bounding_box_max_z,
             face_count, edge_count, vertex_count, is_closed, is_manifold, computed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entity_id,
            props.volume,
            props.surface_area,
            props.center_of_mass_x,
            props.center_of_mass_y,
            props.center_of_mass_z,
            props.bounding_box_min_x,
            props.bounding_box_min_y,
            props.bounding_box_min_z,
            props.bounding_box_max_x,
            props.bounding_box_max_y,
            props.bounding_box_max_z,
            props.face_count,
            props.edge_count,
            props.vertex_count,
            int(props.is_closed),
            int(props.is_manifold),
            props.computed_at
        ))

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
