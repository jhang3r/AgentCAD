#!/usr/bin/env python3
"""
Import existing STEP files from filesystem into the database component library.

Usage:
    python import_step_files.py C:/users/jrdnh/documents/robotics/
"""

import os
import sys
from pathlib import Path
import re

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.shared_state import SharedState


def parse_filename_metadata(filename: str, relative_path: Path = None) -> dict:
    """
    Extract metadata from STEP filename and directory structure.

    Common patterns:
    - motor_mks_mg996r_servo.step -> category: motor, manufacturer: mks, model: mg996r
    - bearing_6006_30x55x13.step -> category: bearing, size: 6006, dimensions: 30x55x13
    - fastener_m5x20_socket_head.step -> category: fastener, size: M5x20, type: socket_head

    Directory structure:
    - company_name/motors/... -> manufacturer: company_name, category: motor
    """
    name_lower = filename.lower().replace('.step', '').replace('.stp', '')
    parts = name_lower.split('_')

    metadata = {
        'original_filename': filename,
        'category': 'custom',
        'manufacturer': 'unknown',
        'part_name': filename
    }

    # Extract manufacturer from directory structure
    # If path is like: "company_name/subfolder/file.step"
    # Then manufacturer = "company_name"
    if relative_path and len(relative_path.parts) > 1:
        # First directory is the company/manufacturer
        manufacturer_dir = relative_path.parts[0]
        metadata['manufacturer'] = manufacturer_dir.replace('_', ' ').title()

    # Detect category from first part or keywords
    if parts:
        first_part = parts[0]
        if first_part in ['motor', 'servo', 'actuator']:
            metadata['category'] = 'motor'
        elif first_part in ['bearing']:
            metadata['category'] = 'bearing'
        elif first_part in ['fastener', 'screw', 'bolt', 'nut']:
            metadata['category'] = 'fastener'
        elif first_part in ['sensor', 'imu', 'encoder']:
            metadata['category'] = 'sensor'
        elif first_part in ['battery', 'cell']:
            metadata['category'] = 'battery'
        elif first_part in ['gear', 'gearbox', 'planetary']:
            metadata['category'] = 'gear'
        elif first_part in ['joint', 'hinge', 'pivot']:
            metadata['category'] = 'joint'
        elif first_part in ['bone', 'link', 'arm', 'leg']:
            metadata['category'] = 'bone'

    # Try to extract bearing size (e.g., 6006)
    bearing_match = re.search(r'(?:^|_)(\d{4})(?:_|$)', name_lower)
    if bearing_match and metadata['category'] == 'bearing':
        metadata['bearing_number'] = bearing_match.group(1)

    # Try to extract fastener size (e.g., M5x20, m8)
    fastener_match = re.search(r'm(\d+)(?:x(\d+))?', name_lower, re.IGNORECASE)
    if fastener_match and metadata['category'] == 'fastener':
        metadata['thread_size'] = f"M{fastener_match.group(1)}"
        if fastener_match.group(2):
            metadata['length_mm'] = int(fastener_match.group(2))

    # Try to extract dimensions (e.g., 30x55x13, 100x50)
    dim_match = re.search(r'(\d+)x(\d+)(?:x(\d+))?', name_lower)
    if dim_match:
        dims = [int(dim_match.group(i)) for i in range(1, 4) if dim_match.group(i)]
        metadata['dimensions_mm'] = dims

    return metadata


def import_step_files(directory: str, dry_run: bool = False):
    """
    Import all STEP files from a directory into the database.

    Args:
        directory: Path to scan for STEP files
        dry_run: If True, just print what would be imported
    """
    directory = Path(directory)

    if not directory.exists():
        print(f"Error: Directory '{directory}' does not exist")
        return

    print(f"{'[DRY RUN] ' if dry_run else ''}Scanning {directory} for STEP files...")
    print()

    # Find all STEP files
    step_files = list(directory.rglob("*.step")) + list(directory.rglob("*.stp")) + list(directory.rglob("*.STEP")) + list(directory.rglob("*.STP"))

    if not step_files:
        print(f"No STEP files found in {directory}")
        return

    print(f"Found {len(step_files)} STEP files")
    print()

    # Initialize database connection
    if not dry_run:
        state = SharedState(execution_id="step_import")

    imported = 0
    skipped = 0

    for step_file in sorted(step_files):
        # Get relative path for better display
        try:
            rel_path = step_file.relative_to(directory)
        except ValueError:
            rel_path = step_file

        # Parse metadata from filename and directory structure
        metadata = parse_filename_metadata(step_file.name, rel_path)

        # Read file
        try:
            with open(step_file, 'rb') as f:
                geometry_data = f.read()
        except Exception as e:
            print(f"✗ Error reading {rel_path}: {e}")
            skipped += 1
            continue

        file_size_kb = len(geometry_data) / 1024

        # Generate part number from path
        part_number = str(rel_path).replace('\\', '/').replace('.step', '').replace('.stp', '').replace('/', '_')

        print(f"{'[DRY RUN] ' if dry_run else ''}Processing: {rel_path}")
        print(f"  Size: {file_size_kb:.1f} KB")
        print(f"  Manufacturer: {metadata['manufacturer']}")
        print(f"  Category: {metadata['category']}")
        print(f"  Part number: {part_number}")

        if dry_run:
            print(f"  Would import as CAD component")
            imported += 1
        else:
            try:
                # Store as CAD component
                component_id = state.store_cad_component(
                    component_name=part_number,
                    component_type=metadata['category'],
                    subsystem='library',  # Mark as library component
                    geometry_data=geometry_data,
                    file_format='STEP',
                    metadata={
                        'source_path': str(step_file),
                        'parsed_metadata': metadata,
                        'file_size_bytes': len(geometry_data)
                    },
                    created_by='import_script'
                )

                # If it has good metadata, also add to component library
                if metadata['category'] != 'custom':
                    try:
                        state.add_component_to_library(
                            part_number=part_number,
                            manufacturer=metadata.get('manufacturer', 'Unknown'),
                            part_name=step_file.stem,
                            category=metadata['category'],
                            specifications=metadata,
                            geometry_id=component_id
                        )
                        print(f"  ✓ Imported as component {component_id} and added to library")
                    except Exception as e:
                        # Library add failed, but component stored
                        print(f"  ✓ Imported as component {component_id} (library add failed: {e})")
                else:
                    print(f"  ✓ Imported as component {component_id}")

                imported += 1

            except Exception as e:
                print(f"  ✗ Failed to import: {e}")
                skipped += 1

        print()

    if not dry_run:
        state.close()

    print("=" * 60)
    print(f"{'[DRY RUN] ' if dry_run else ''}Import complete!")
    print(f"  Imported: {imported}")
    print(f"  Skipped: {skipped}")
    print("=" * 60)

    if not dry_run:
        print("\nYou can now:")
        print("  1. View components: python -c \"from utils.shared_state import SharedState; s = SharedState(); print(s.get_subsystem_components('library'))\"")
        print("  2. Search library: python -c \"from utils.shared_state import SharedState; s = SharedState(); print(s.search_component_library())\"")
        print("  3. View in Supabase Studio: http://localhost:3000")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Import STEP files into AgentCAD database')
    parser.add_argument('directory', help='Directory to scan for STEP files')
    parser.add_argument('--dry-run', action='store_true', help='Preview what would be imported without actually importing')
    parser.add_argument('--recursive', action='store_true', default=True, help='Scan subdirectories (default: True)')

    args = parser.parse_args()

    import_step_files(args.directory, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
