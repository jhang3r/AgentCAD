#!/usr/bin/env python3
"""
Database initialization script for AgentCAD humanoid design system.

This script:
1. Waits for PostgreSQL to be ready
2. Migrates existing filesystem data to database (if present)
3. Initializes default values
"""

import os
import sys
import time
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

load_dotenv()


def wait_for_db(max_retries=30, delay=2):
    """Wait for PostgreSQL to be ready."""
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/agentcad")

    print(f"Waiting for database to be ready...")
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(db_url)
            conn.close()
            print("✓ Database is ready!")
            return True
        except psycopg2.OperationalError:
            print(f"  Attempt {i+1}/{max_retries}: Database not ready, waiting {delay}s...")
            time.sleep(delay)

    print("✗ Database failed to become ready")
    return False


def migrate_filesystem_data_to_db():
    """Migrate existing filesystem JSON data to database (if present)."""
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/agentcad")
    shared_state_path = Path(__file__).parent.parent / "shared_state"

    if not shared_state_path.exists():
        print("No existing shared_state directory found, skipping migration")
        return

    print("\n=== Migrating filesystem data to database ===")

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    try:
        # Migrate global constraints
        constraints_file = shared_state_path / "constraints" / "global.json"
        if constraints_file.exists():
            print("  Migrating global constraints...")
            with open(constraints_file) as f:
                data = json.load(f)

            cur.execute("""
                INSERT INTO global_constraints
                (version, total_mass_kg_max, total_cost_usd_max, height_m, voltage_v, budget_allocations)
                VALUES (1, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                data.get('total_mass_kg_max', 45.0),
                data.get('total_cost_usd_max', 15000.0),
                data.get('height_m', 1.75),
                data.get('voltage_v', 48),
                Json(data.get('budget_allocations', {}))
            ))

        # Migrate subsystem statuses
        subsystems_dir = shared_state_path / "subsystems"
        if subsystems_dir.exists():
            for subsystem_dir in subsystems_dir.iterdir():
                if not subsystem_dir.is_dir():
                    continue

                subsystem_name = subsystem_dir.name
                status_file = subsystem_dir / "status.json"

                if status_file.exists():
                    print(f"  Migrating {subsystem_name} status...")
                    with open(status_file) as f:
                        status = json.load(f)

                    cur.execute("""
                        UPDATE subsystems SET
                            state = %s,
                            current_mass_kg = %s,
                            current_cost_usd = %s,
                            current_power_w = %s,
                            iteration = %s,
                            within_budget = %s,
                            metadata = %s
                        WHERE name = %s
                    """, (
                        status.get('state', 'not_started'),
                        status.get('current_mass_kg', 0),
                        status.get('current_cost_usd', 0),
                        status.get('current_power_w', 0),
                        status.get('iteration', 0),
                        status.get('within_budget', True),
                        Json(status),
                        subsystem_name
                    ))

                # Migrate requirements
                req_file = subsystem_dir / "requirements.json"
                if req_file.exists():
                    print(f"  Migrating {subsystem_name} requirements...")
                    with open(req_file) as f:
                        requirements = json.load(f)

                    cur.execute("""
                        INSERT INTO subsystem_requirements (subsystem_name, version, requirements, created_by)
                        VALUES (%s, 1, %s, 'migrated')
                        ON CONFLICT DO NOTHING
                    """, (subsystem_name, Json(requirements)))

                # Migrate interfaces
                interfaces_file = subsystem_dir / "interfaces.json"
                if interfaces_file.exists():
                    print(f"  Migrating {subsystem_name} interfaces...")
                    with open(interfaces_file) as f:
                        interfaces = json.load(f)

                    cur.execute("""
                        INSERT INTO subsystem_interfaces (subsystem_name, version, interfaces)
                        VALUES (%s, 1, %s)
                        ON CONFLICT DO NOTHING
                    """, (subsystem_name, Json(interfaces)))

                # Migrate design data
                design_files = list(subsystem_dir.glob("*design*.json"))
                if design_files:
                    print(f"  Migrating {subsystem_name} design...")
                    with open(design_files[0]) as f:
                        design = json.load(f)

                    cur.execute("""
                        INSERT INTO subsystem_designs (subsystem_name, version, design_data)
                        VALUES (%s, 1, %s)
                        ON CONFLICT DO NOTHING
                    """, (subsystem_name, Json(design)))

        # Migrate conflicts
        conflicts_file = shared_state_path / "conflicts" / "active.json"
        if conflicts_file.exists():
            print("  Migrating conflicts...")
            with open(conflicts_file) as f:
                data = json.load(f)

            for conflict in data.get('conflicts', []):
                cur.execute("""
                    INSERT INTO conflicts (
                        conflict_id, severity, priority, source_agent, target_agent,
                        description, details, status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    conflict.get('id'),
                    conflict.get('severity', 'medium'),
                    3,  # default priority
                    conflict.get('source_agent'),
                    conflict.get('target_agent'),
                    conflict.get('description'),
                    Json(conflict.get('details', {})),
                    conflict.get('status', 'open')
                ))

        conn.commit()
        print("✓ Migration complete!")

    except Exception as e:
        conn.rollback()
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def initialize_default_config():
    """Initialize default configuration from global_requirements.json."""
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/agentcad")
    config_file = Path(__file__).parent.parent / "config" / "global_requirements.json"

    if not config_file.exists():
        print("No global_requirements.json found, skipping default config")
        return

    print("\n=== Initializing default configuration ===")

    with open(config_file) as f:
        config = json.load(f)

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    try:
        # Check if constraints already exist
        cur.execute("SELECT COUNT(*) FROM global_constraints")
        if cur.fetchone()[0] == 0:
            print("  Creating default global constraints...")

            # Default budget allocation
            budget_allocations = {
                "skeleton": {"mass_kg": 15.0, "cost_usd": 3000.0},
                "actuation": {"mass_kg": 12.0, "cost_usd": 6000.0, "power_w": 800.0},
                "power": {"mass_kg": 8.0, "cost_usd": 2000.0, "power_w": 50.0},
                "sensing": {"mass_kg": 3.0, "cost_usd": 2500.0, "power_w": 50.0},
                "shell": {"mass_kg": 5.0, "cost_usd": 1000.0},
                "reserve": {"mass_kg": 2.0, "cost_usd": 500.0}
            }

            cur.execute("""
                INSERT INTO global_constraints
                (version, total_mass_kg_max, total_cost_usd_max, height_m, voltage_v, budget_allocations)
                VALUES (1, %s, %s, %s, 48, %s)
            """, (
                config['physical']['mass_kg_max'],
                config['constraints']['cost_usd_max'],
                config['physical']['height_m'],
                Json(budget_allocations)
            ))

            conn.commit()
            print("✓ Default configuration created!")
        else:
            print("  Global constraints already exist, skipping")

    except Exception as e:
        conn.rollback()
        print(f"✗ Initialization failed: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def main():
    """Main initialization routine."""
    print("=" * 60)
    print("AgentCAD Database Initialization")
    print("=" * 60)

    # Wait for database
    if not wait_for_db():
        sys.exit(1)

    # Migrate existing data
    migrate_filesystem_data_to_db()

    # Initialize default config
    initialize_default_config()

    print("\n" + "=" * 60)
    print("✓ Database initialization complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Start the design system: python humanoid_agents/orchestration_helpers.py")
    print("  2. View database UI: http://localhost:3000 (Supabase Studio)")
    print("  3. Access database directly: psql postgresql://postgres:postgres@localhost:5432/agentcad")


if __name__ == "__main__":
    main()
