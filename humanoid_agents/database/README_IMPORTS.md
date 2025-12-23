# Component Library Import Scripts

Import your existing CAD files and actuator specifications into the AgentCAD database.

## Quick Start

### 1. Start the Database

```bash
# From project root
docker-compose up -d

# Initialize database
cd humanoid_agents
python database/init_db.py
```

### 2. Import STEP Files

```bash
# Import all STEP files from your robotics directory
python database/import_step_files.py C:/users/jrdnh/documents/robotics/

# Preview what would be imported (dry run)
python database/import_step_files.py C:/users/jrdnh/documents/robotics/ --dry-run
```

### 3. Import Actuator Specs from Excel

```bash
# Import all Excel files with actuator specs
python database/import_actuator_specs.py C:/users/jrdnh/documents/robotics/

# Preview what would be imported (dry run)
python database/import_actuator_specs.py C:/users/jrdnh/documents/robotics/ --dry-run
```

## STEP File Import

### What It Does

- Scans directory recursively for `.step`, `.stp`, `.STEP`, `.STP` files
- Parses filenames to extract metadata (category, manufacturer, size, etc.)
- Stores binary STEP data in `cad_components` table
- Adds well-categorized components to `component_library` table

### Filename Parsing

The script tries to intelligently parse filenames:

**Examples:**
```
motor_mks_mg996r_servo.step
→ Category: motor, Manufacturer: mks, Model: mg996r

bearing_6006_30x55x13.step
→ Category: bearing, Number: 6006, Dimensions: [30, 55, 13] mm

fastener_m5x20_socket_head.step
→ Category: fastener, Thread: M5, Length: 20mm, Type: socket_head

bone_femur_right_v2.step
→ Category: bone, Name: femur_right

gear_planetary_50_1_reduction.step
→ Category: gear, Type: planetary, Ratio: 50:1
```

**Recognized Categories:**
- `motor`, `servo`, `actuator`
- `bearing`
- `fastener`, `screw`, `bolt`, `nut`
- `sensor`, `imu`, `encoder`
- `battery`, `cell`
- `gear`, `gearbox`, `planetary`
- `joint`, `hinge`, `pivot`
- `bone`, `link`, `arm`, `leg`

### Usage

```bash
# Basic import
python database/import_step_files.py /path/to/step/files/

# Dry run (preview)
python database/import_step_files.py /path/to/step/files/ --dry-run

# Import from multiple directories
python database/import_step_files.py /path/one/
python database/import_step_files.py /path/two/
```

### Output

```
Scanning C:/users/jrdnh/documents/robotics/ for STEP files...

Found 47 STEP files

Processing: motors/brushless/turnigy_2836.step
  Size: 234.5 KB
  Category: motor
  Part number: motors_brushless_turnigy_2836
  ✓ Imported as component a1b2c3d4-... and added to library

Processing: bearings/6006_zz.step
  Size: 45.2 KB
  Category: bearing
  Part number: bearings_6006_zz
  ✓ Imported as component e5f6g7h8-... and added to library

============================================================
Import complete!
  Imported: 45
  Skipped: 2
============================================================
```

## Excel Import

### What It Does

- Reads `.xls` and `.xlsx` files
- Automatically detects column headers (flexible matching)
- Extracts actuator specifications
- Stores in `component_library` table with full specs

### Supported Column Headers

The script automatically detects these column patterns (case-insensitive):

**Required:**
- Part Number: `part_number`, `part_no`, `model`, `model_number`, `pn`

**Optional:**
- Manufacturer: `manufacturer`, `mfr`, `brand`, `maker`
- Name: `name`, `description`, `part_name`
- Torque: `torque`, `torque_nm`, `stall_torque`, `max_torque`
- Speed: `speed`, `speed_rpm`, `no_load_speed`, `rpm`
- Voltage: `voltage`, `voltage_v`, `operating_voltage`
- Current: `current`, `current_a`, `stall_current`
- Power: `power`, `power_w`, `watts`
- Mass: `mass`, `mass_kg`, `weight`, `weight_kg`, `mass_g`
- Cost: `cost`, `cost_usd`, `price`, `price_usd`
- Dimensions: `dimensions`, `size`, `length_mm`, `diameter_mm`
- Gear Ratio: `gear_ratio`, `ratio`, `reduction`

### Example Excel Format

| Part Number | Manufacturer | Torque (Nm) | Speed (RPM) | Voltage (V) | Cost ($) | Mass (g) |
|-------------|--------------|-------------|-------------|-------------|----------|----------|
| MG996R      | TowerPro     | 0.98        | 60          | 4.8-6.0     | 8.50     | 55       |
| DS3218      | DSSERVO      | 20.0        | 60          | 6.8         | 24.99    | 60       |
| MKS DS75K   | MKS          | 25.0        | 60          | 7.4         | 89.99    | 75       |

### Usage

```bash
# Import all Excel files
python database/import_actuator_specs.py /path/to/excel/files/

# Dry run (preview)
python database/import_actuator_specs.py /path/to/excel/files/ --dry-run

# Non-recursive (only current directory)
python database/import_actuator_specs.py /path/to/excel/files/ --no-recursive
```

### Output

```
Scanning C:/users/jrdnh/documents/robotics/ for Excel files...
Found 3 Excel files

Processing: servo_motors_catalog.xlsx
  Found 24 rows with columns: part_number, manufacturer, torque_nm, speed_rpm, voltage_v, cost_usd, mass_g
  Detected columns: {'part_number': 'part_number', 'manufacturer': 'manufacturer', 'torque': 'torque_nm', ...}
  ✓ [1] Imported: MG996R - TowerPro Servo Motor
  ✓ [2] Imported: DS3218 - DSSERVO High Torque
  ...

============================================================
Import complete!
  Total imported: 68
  Total skipped: 2
============================================================
```

## Querying Imported Data

### Python

```python
from utils.shared_state import SharedState

state = SharedState()

# Search for motors
motors = state.search_component_library(category='motor')
print(f"Found {len(motors)} motors")

# Search with filters
affordable_motors = state.search_component_library(
    category='motor',
    max_cost_usd=50.0
)

# Get CAD geometry for a component
component = state.get_cad_component('motors_brushless_turnigy_2836')
print(f"STEP file size: {len(component['geometry_data'])} bytes")

# Export to file
state.export_cad_component_to_file(
    'motors_brushless_turnigy_2836',
    '/tmp/turnigy_2836.step'
)

state.close()
```

### SQL (via psql or Supabase Studio)

```sql
-- View all imported components
SELECT * FROM component_library ORDER BY category, part_number;

-- Find motors under $50
SELECT part_number, part_name, cost_usd, specifications->>'torque' as torque
FROM component_library
WHERE category = 'motor' AND cost_usd < 50
ORDER BY cost_usd;

-- View CAD components by subsystem
SELECT component_name, component_type, file_size_bytes / 1024 as size_kb
FROM cad_components
WHERE subsystem_name = 'library'
ORDER BY component_type, component_name;

-- Component statistics
SELECT * FROM component_stats;
```

### Supabase Studio (GUI)

1. Open http://localhost:3000
2. Navigate to "Table Editor"
3. Select `component_library` or `cad_components`
4. Use filters and search

## Troubleshooting

### "ModuleNotFoundError: No module named 'openpyxl'"

```bash
pip install -r requirements.txt
```

### "Database connection failed"

```bash
# Make sure database is running
docker-compose up -d

# Wait for it to be ready
python database/init_db.py
```

### "Duplicate key error"

The scripts will update existing entries if part numbers match. To force reimport:

```sql
-- Delete all library components
DELETE FROM component_library WHERE true;
DELETE FROM cad_components WHERE subsystem_name = 'library';

-- Then re-run import scripts
```

### Excel file has weird encoding

Try saving it as `.xlsx` format in Excel first, or use:

```python
# Manual fix
import pandas as pd
df = pd.read_excel('file.xls', encoding='latin1')
df.to_excel('file_fixed.xlsx', index=False)
```

## Advanced Usage

### Batch Import Script

Create `import_all.sh`:

```bash
#!/bin/bash

echo "Starting component library import..."

# Start database
docker-compose up -d
sleep 5

# Initialize
python humanoid_agents/database/init_db.py

# Import STEP files from multiple sources
python humanoid_agents/database/import_step_files.py C:/users/jrdnh/documents/robotics/cad/
python humanoid_agents/database/import_step_files.py C:/users/jrdnh/downloads/step_files/

# Import Excel specs
python humanoid_agents/database/import_actuator_specs.py C:/users/jrdnh/documents/robotics/specs/
python humanoid_agents/database/import_actuator_specs.py C:/users/jrdnh/documents/datasheets/

echo "Import complete!"
echo "View at: http://localhost:3000"
```

### Custom Metadata

Modify `import_step_files.py` to add custom metadata:

```python
# After line with metadata['original_filename'] = filename
metadata['custom_field'] = 'custom_value'
metadata['supplier'] = 'AliExpress'
metadata['date_added'] = '2025-01-15'
```

## Next Steps

After importing:
1. View components in Supabase Studio: http://localhost:3000
2. Use components in agent prompts (agents can search library)
3. Export assemblies with selected components
4. Generate BOMs with costs and suppliers
