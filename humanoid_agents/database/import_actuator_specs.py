#!/usr/bin/env python3
"""
Import actuator specifications from Excel files into the component library.

Usage:
    python import_actuator_specs.py C:/users/jrdnh/documents/robotics/*.xls
    python import_actuator_specs.py C:/users/jrdnh/documents/robotics/ --recursive
"""

import os
import sys
from pathlib import Path
import pandas as pd
import re

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.shared_state import SharedState


def clean_column_name(col: str) -> str:
    """Convert column header to snake_case."""
    col = col.strip().lower()
    col = re.sub(r'[^\w\s]', '', col)
    col = re.sub(r'\s+', '_', col)
    return col


def parse_value(value):
    """Parse Excel cell value, handling units and ranges."""
    if pd.isna(value):
        return None

    # Convert to string
    value_str = str(value).strip()

    # Try to extract numeric value
    numeric_match = re.search(r'([\d.]+)', value_str)
    if numeric_match:
        try:
            return float(numeric_match.group(1))
        except ValueError:
            pass

    return value_str


def import_excel_file(file_path: Path, state: SharedState, dry_run: bool = False) -> tuple:
    """
    Import actuators from a single Excel file.

    Returns:
        (imported_count, skipped_count)
    """
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Processing: {file_path.name}")

    try:
        # Try to read Excel file (supports both .xls and .xlsx)
        df = pd.read_excel(file_path, sheet_name=0)  # Read first sheet
    except Exception as e:
        print(f"  ✗ Error reading file: {e}")
        return (0, 1)

    # Clean column names
    df.columns = [clean_column_name(col) for col in df.columns]

    print(f"  Found {len(df)} rows with columns: {', '.join(df.columns)}")

    imported = 0
    skipped = 0

    # Detect column mappings (flexible matching)
    column_mappings = {
        'part_number': ['part_number', 'part_no', 'model', 'model_number', 'pn'],
        'manufacturer': ['manufacturer', 'mfr', 'brand', 'maker'],
        'name': ['name', 'description', 'part_name', 'product_name'],
        'torque': ['torque', 'torque_nm', 'stall_torque', 'max_torque'],
        'speed': ['speed', 'speed_rpm', 'no_load_speed', 'rpm'],
        'voltage': ['voltage', 'voltage_v', 'operating_voltage', 'v'],
        'current': ['current', 'current_a', 'stall_current', 'amps'],
        'power': ['power', 'power_w', 'watts'],
        'mass': ['mass', 'mass_kg', 'weight', 'weight_kg', 'mass_g'],
        'cost': ['cost', 'cost_usd', 'price', 'price_usd', 'price_'],
        'dimensions': ['dimensions', 'size', 'length_mm', 'diameter_mm'],
        'gear_ratio': ['gear_ratio', 'ratio', 'reduction'],
    }

    # Find actual column names in the DataFrame
    col_map = {}
    for key, possible_names in column_mappings.items():
        for possible in possible_names:
            if possible in df.columns:
                col_map[key] = possible
                break

    print(f"  Detected columns: {col_map}")

    # Process each row
    for idx, row in df.iterrows():
        # Skip if missing part number
        if 'part_number' not in col_map or pd.isna(row[col_map['part_number']]):
            skipped += 1
            continue

        part_number = str(row[col_map['part_number']]).strip()

        # Build specifications dictionary
        specs = {}
        for key, col_name in col_map.items():
            if key != 'part_number':  # Don't include part_number in specs
                value = parse_value(row[col_name])
                if value is not None:
                    specs[key] = value

        # Extract key values
        manufacturer = specs.get('manufacturer', 'Unknown')
        name = specs.get('name', part_number)
        torque = specs.get('torque')
        cost_usd = specs.get('cost')
        mass_kg = specs.get('mass')

        # Convert mass from grams if needed
        if mass_kg and mass_kg > 10:  # Assume it's in grams if > 10
            mass_kg = mass_kg / 1000
            specs['mass_kg'] = mass_kg

        if dry_run:
            print(f"  [{idx+1}] Would import: {part_number} - {name}")
            if torque:
                print(f"      Torque: {torque} Nm")
            if cost_usd:
                print(f"      Cost: ${cost_usd}")
            imported += 1
        else:
            try:
                state.add_component_to_library(
                    part_number=part_number,
                    manufacturer=manufacturer,
                    part_name=name,
                    category='motor',
                    specifications=specs,
                    cost_usd=cost_usd,
                    mass_kg=mass_kg
                )
                print(f"  ✓ [{idx+1}] Imported: {part_number} - {name}")
                imported += 1
            except Exception as e:
                print(f"  ✗ [{idx+1}] Failed to import {part_number}: {e}")
                skipped += 1

    return (imported, skipped)


def import_actuator_specs(directory: str, dry_run: bool = False, recursive: bool = True):
    """
    Import all Excel files with actuator specs from a directory.

    Args:
        directory: Path to scan for Excel files
        dry_run: If True, just print what would be imported
        recursive: Scan subdirectories
    """
    directory = Path(directory)

    if not directory.exists():
        print(f"Error: Directory '{directory}' does not exist")
        return

    print(f"{'[DRY RUN] ' if dry_run else ''}Scanning {directory} for Excel files...")

    # Find all Excel files
    if recursive:
        excel_files = list(directory.rglob("*.xls")) + list(directory.rglob("*.xlsx"))
    else:
        excel_files = list(directory.glob("*.xls")) + list(directory.glob("*.xlsx"))

    # Filter out temp files
    excel_files = [f for f in excel_files if not f.name.startswith('~$')]

    if not excel_files:
        print(f"No Excel files found in {directory}")
        return

    print(f"Found {len(excel_files)} Excel files")

    # Initialize database connection
    state = None
    if not dry_run:
        state = SharedState(execution_id="excel_import")

    total_imported = 0
    total_skipped = 0

    try:
        for excel_file in sorted(excel_files):
            imported, skipped = import_excel_file(excel_file, state, dry_run)
            total_imported += imported
            total_skipped += skipped

    finally:
        if state:
            state.close()

    print("\n" + "=" * 60)
    print(f"{'[DRY RUN] ' if dry_run else ''}Import complete!")
    print(f"  Total imported: {total_imported}")
    print(f"  Total skipped: {total_skipped}")
    print("=" * 60)

    if not dry_run and total_imported > 0:
        print("\nYou can now:")
        print("  1. Search motors: python -c \"from utils.shared_state import SharedState; s = SharedState(); print(s.search_component_library(category='motor'))\"")
        print("  2. View all library: python -c \"from utils.shared_state import SharedState; s = SharedState(); print(s.search_component_library())\"")
        print("  3. View in Supabase Studio: http://localhost:3000 -> component_library table")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Import actuator specs from Excel files into AgentCAD database')
    parser.add_argument('directory', help='Directory to scan for Excel files')
    parser.add_argument('--dry-run', action='store_true', help='Preview what would be imported without actually importing')
    parser.add_argument('--recursive', '-r', action='store_true', default=True, help='Scan subdirectories (default: True)')

    args = parser.parse_args()

    import_actuator_specs(args.directory, dry_run=args.dry_run, recursive=args.recursive)


if __name__ == "__main__":
    main()
