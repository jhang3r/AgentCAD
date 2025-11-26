"""Manual end-to-end tests for the CAD learning environment.

Run this to verify the system is working correctly.
"""
import json
import subprocess
import sys
from pathlib import Path


class CADTester:
    """Helper class for manual testing."""

    def __init__(self):
        self.test_count = 0
        self.pass_count = 0
        self.fail_count = 0

    def call_cli(self, request: dict) -> dict:
        """Call CLI with JSON-RPC request."""
        input_data = json.dumps(request) + "\n"
        result = subprocess.run(
            [sys.executable, "-m", "src.agent_interface.cli"],
            input=input_data,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )

        if result.returncode != 0:
            raise RuntimeError(f"CLI failed: {result.stderr}")

        return json.loads(result.stdout.strip())

    def test(self, name: str, fn):
        """Run a test and track results."""
        self.test_count += 1
        print(f"\n{'='*60}")
        print(f"Test {self.test_count}: {name}")
        print('='*60)

        try:
            fn()
            self.pass_count += 1
            print(f"[PASS]")
        except Exception as e:
            self.fail_count += 1
            print(f"[FAIL]: {e}")
            import traceback
            traceback.print_exc()

    def assert_success(self, response: dict, operation: str):
        """Assert response is successful."""
        assert "result" in response, f"{operation} returned error: {response.get('error')}"
        assert response["result"]["status"] == "success", f"{operation} failed"

    def print_summary(self):
        """Print test summary."""
        print(f"\n{'='*60}")
        print(f"TEST SUMMARY")
        print('='*60)
        print(f"Total tests: {self.test_count}")
        print(f"Passed: {self.pass_count}")
        print(f"Failed: {self.fail_count}")
        print(f"Success rate: {100 * self.pass_count / self.test_count:.1f}%")


def main():
    tester = CADTester()

    # Test 1: Basic geometry creation
    def test_geometry_creation():
        print("\n1. Creating a point...")
        point = tester.call_cli({
            "jsonrpc": "2.0",
            "method": "entity.create.point",
            "params": {"coordinates": [10.0, 20.0, 30.0]},
            "id": 1
        })
        tester.assert_success(point, "Point creation")
        point_id = point["result"]["data"]["entity_id"]
        print(f"   Created point: {point_id}")
        assert point["result"]["data"]["coordinates"] == [10.0, 20.0, 30.0]

        print("\n2. Creating a line...")
        line = tester.call_cli({
            "jsonrpc": "2.0",
            "method": "entity.create.line",
            "params": {"start": [0.0, 0.0], "end": [10.0, 0.0]},
            "id": 2
        })
        tester.assert_success(line, "Line creation")
        line_id = line["result"]["data"]["entity_id"]
        print(f"   Created line: {line_id}")
        assert line["result"]["data"]["length"] == 10.0

        print("\n3. Creating a circle...")
        circle = tester.call_cli({
            "jsonrpc": "2.0",
            "method": "entity.create.circle",
            "params": {"center": [5.0, 5.0], "radius": 3.0},
            "id": 3
        })
        tester.assert_success(circle, "Circle creation")
        circle_id = circle["result"]["data"]["entity_id"]
        print(f"   Created circle: {circle_id}")
        assert 28.0 < circle["result"]["data"]["area"] < 29.0  # π*r² ≈ 28.27

        print("\n4. Listing entities...")
        entities = tester.call_cli({
            "jsonrpc": "2.0",
            "method": "entity.list",
            "params": {},
            "id": 4
        })
        tester.assert_success(entities, "Entity list")
        print(f"   Total entities: {entities['result']['data']['total_count']}")
        assert entities["result"]["data"]["total_count"] >= 3

        print("\n5. Querying an entity...")
        query = tester.call_cli({
            "jsonrpc": "2.0",
            "method": "entity.query",
            "params": {"entity_id": circle_id},
            "id": 5
        })
        tester.assert_success(query, "Entity query")
        print(f"   Queried entity type: {query['result']['data']['entity_type']}")
        assert query["result"]["data"]["radius"] == 3.0

    tester.test("Basic Geometry Creation", test_geometry_creation)

    # Test 2: Constraint solving
    def test_constraints():
        print("\n1. Creating two lines...")
        line1 = tester.call_cli({
            "jsonrpc": "2.0",
            "method": "entity.create.line",
            "params": {"start": [0.0, 0.0], "end": [10.0, 0.0]},
            "id": 1
        })
        line1_id = line1["result"]["data"]["entity_id"]

        line2 = tester.call_cli({
            "jsonrpc": "2.0",
            "method": "entity.create.line",
            "params": {"start": [0.0, 0.0], "end": [0.0, 10.0]},
            "id": 2
        })
        line2_id = line2["result"]["data"]["entity_id"]
        print(f"   Created lines: {line1_id}, {line2_id}")

        print("\n2. Applying perpendicular constraint...")
        constraint = tester.call_cli({
            "jsonrpc": "2.0",
            "method": "constraint.apply",
            "params": {
                "constraint_type": "perpendicular",
                "entity_ids": [line1_id, line2_id]
            },
            "id": 3
        })
        tester.assert_success(constraint, "Constraint apply")
        constraint_id = constraint["result"]["data"]["constraint_id"]
        print(f"   Applied constraint: {constraint_id}")
        assert constraint["result"]["data"]["satisfaction_status"] == "satisfied"

        print("\n3. Checking constraint status...")
        status = tester.call_cli({
            "jsonrpc": "2.0",
            "method": "constraint.status",
            "params": {"constraint_id": constraint_id},
            "id": 4
        })
        tester.assert_success(status, "Constraint status")
        print(f"   Constraint satisfied: {status['result']['data']['satisfaction_status']}")
        assert status["result"]["data"]["satisfaction_status"] == "satisfied"

    tester.test("Constraint Solving", test_constraints)

    # Test 3: Solid modeling
    def test_solid_modeling():
        print("\n1. Creating a rectangular sketch...")
        lines = []
        corners = [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]]
        for i in range(4):
            line = tester.call_cli({
                "jsonrpc": "2.0",
                "method": "entity.create.line",
                "params": {
                    "start": corners[i],
                    "end": corners[(i + 1) % 4]
                },
                "id": i + 1
            })
            lines.append(line["result"]["data"]["entity_id"])
        print(f"   Created sketch with 4 lines")

        print("\n2. Extruding to create a box...")
        extrude = tester.call_cli({
            "jsonrpc": "2.0",
            "method": "solid.extrude",
            "params": {
                "entity_ids": lines,
                "distance": 10.0
            },
            "id": 5
        })
        tester.assert_success(extrude, "Extrude")
        box_id = extrude["result"]["data"]["entity_id"]
        print(f"   Created box: {box_id}")
        print(f"   Volume: {extrude['result']['data']['volume']}")
        assert 950 < extrude["result"]["data"]["volume"] < 1050  # Should be 1000

        print("\n3. Creating another box...")
        lines2 = []
        corners2 = [[5.0, 5.0], [15.0, 5.0], [15.0, 15.0], [5.0, 15.0]]
        for i in range(4):
            line = tester.call_cli({
                "jsonrpc": "2.0",
                "method": "entity.create.line",
                "params": {
                    "start": corners2[i],
                    "end": corners2[(i + 1) % 4]
                },
                "id": i + 6
            })
            lines2.append(line["result"]["data"]["entity_id"])

        extrude2 = tester.call_cli({
            "jsonrpc": "2.0",
            "method": "solid.extrude",
            "params": {
                "entity_ids": lines2,
                "distance": 10.0
            },
            "id": 10
        })
        box2_id = extrude2["result"]["data"]["entity_id"]
        print(f"   Created second box: {box2_id}")

        print("\n4. Performing boolean union...")
        union = tester.call_cli({
            "jsonrpc": "2.0",
            "method": "solid.boolean",
            "params": {
                "operation": "union",
                "entity_ids": [box_id, box2_id]
            },
            "id": 11
        })
        tester.assert_success(union, "Boolean union")
        union_id = union["result"]["data"]["entity_id"]
        print(f"   Created union: {union_id}")
        print(f"   Union volume: {union['result']['data']['volume']}")
        assert union["result"]["data"]["volume"] > 1400  # Should be larger than one box

    tester.test("Solid Modeling", test_solid_modeling)

    # Test 4: File export
    def test_file_export():
        print("\n1. Creating entities to export...")
        point = tester.call_cli({
            "jsonrpc": "2.0",
            "method": "entity.create.point",
            "params": {"coordinates": [1.0, 2.0, 3.0]},
            "id": 1
        })

        circle = tester.call_cli({
            "jsonrpc": "2.0",
            "method": "entity.create.circle",
            "params": {"center": [0.0, 0.0], "radius": 5.0},
            "id": 2
        })
        circle_id = circle["result"]["data"]["entity_id"]

        print("\n2. Exporting to JSON...")
        export_json = tester.call_cli({
            "jsonrpc": "2.0",
            "method": "file.export",
            "params": {
                "file_path": "manual_test_export.json",
                "format": "json"
            },
            "id": 3
        })
        tester.assert_success(export_json, "JSON export")
        print(f"   Exported {export_json['result']['data']['entity_count']} entities")
        print(f"   File size: {export_json['result']['data']['file_size']} bytes")
        assert export_json["result"]["data"]["entity_count"] >= 2

        print("\n3. Creating a solid and exporting to STL...")
        lines = []
        for i in range(4):
            corners = [[0.0, 0.0], [5.0, 0.0], [5.0, 5.0], [0.0, 5.0]]
            line = tester.call_cli({
                "jsonrpc": "2.0",
                "method": "entity.create.line",
                "params": {
                    "start": corners[i],
                    "end": corners[(i + 1) % 4]
                },
                "id": i + 4
            })
            lines.append(line["result"]["data"]["entity_id"])

        solid = tester.call_cli({
            "jsonrpc": "2.0",
            "method": "solid.extrude",
            "params": {
                "entity_ids": lines,
                "distance": 5.0
            },
            "id": 8
        })
        solid_id = solid["result"]["data"]["entity_id"]

        export_stl = tester.call_cli({
            "jsonrpc": "2.0",
            "method": "file.export",
            "params": {
                "file_path": "manual_test_export.stl",
                "format": "stl",
                "entity_ids": [solid_id]
            },
            "id": 9
        })
        tester.assert_success(export_stl, "STL export")
        print(f"   Exported STL with {export_stl['result']['data']['triangle_count']} triangles")
        print(f"   File size: {export_stl['result']['data']['file_size']} bytes")
        assert export_stl["result"]["data"]["triangle_count"] > 0

        print("\n4. Importing from JSON...")
        import_json = tester.call_cli({
            "jsonrpc": "2.0",
            "method": "file.import",
            "params": {
                "file_path": "manual_test_export.json",
                "format": "json"
            },
            "id": 10
        })
        tester.assert_success(import_json, "JSON import")
        print(f"   Imported {import_json['result']['data']['entity_count']} entities")

    tester.test("File Import/Export", test_file_export)

    # Test 5: History tracking
    def test_history():
        print("\n1. Checking initial history...")
        history = tester.call_cli({
            "jsonrpc": "2.0",
            "method": "history.list",
            "params": {},
            "id": 1
        })
        tester.assert_success(history, "History list")
        initial_count = history["result"]["data"]["total_count"]
        print(f"   History has {initial_count} operations")
        print(f"   Can undo: {history['result']['data']['can_undo']}")
        print(f"   Can redo: {history['result']['data']['can_redo']}")

        print("\n2. Testing undo when no operations...")
        try:
            undo = tester.call_cli({
                "jsonrpc": "2.0",
                "method": "history.undo",
                "params": {},
                "id": 2
            })
            # Should get an error
            if "error" in undo:
                print(f"   Got expected error: {undo['error']['message']}")
            else:
                print(f"   Undo worked (operation count was > 0)")
        except Exception as e:
            print(f"   Got expected error: {e}")

    tester.test("History Tracking", test_history)

    # Test 6: Error handling
    def test_error_handling():
        print("\n1. Testing invalid coordinates...")
        response = tester.call_cli({
            "jsonrpc": "2.0",
            "method": "entity.create.point",
            "params": {"coordinates": [1e100, 2e100, 3e100]},  # Out of bounds
            "id": 1
        })
        assert "error" in response, "Should get error for out of bounds"
        print(f"   Got expected error: {response['error']['message']}")

        print("\n2. Testing invalid method...")
        response = tester.call_cli({
            "jsonrpc": "2.0",
            "method": "invalid.method",
            "params": {},
            "id": 2
        })
        assert "error" in response, "Should get error for invalid method"
        print(f"   Got expected error: {response['error']['message']}")

        print("\n3. Testing missing required parameter...")
        response = tester.call_cli({
            "jsonrpc": "2.0",
            "method": "entity.create.circle",
            "params": {"center": [0.0, 0.0]},  # Missing radius
            "id": 3
        })
        assert "error" in response, "Should get error for missing parameter"
        print(f"   Got expected error: {response['error']['message']}")

        print("\n4. Testing invalid constraint type...")
        # Create two lines
        line1 = tester.call_cli({
            "jsonrpc": "2.0",
            "method": "entity.create.line",
            "params": {"start": [0.0, 0.0], "end": [10.0, 0.0]},
            "id": 4
        })
        line1_id = line1["result"]["data"]["entity_id"]

        line2 = tester.call_cli({
            "jsonrpc": "2.0",
            "method": "entity.create.line",
            "params": {"start": [0.0, 0.0], "end": [0.0, 10.0]},
            "id": 5
        })
        line2_id = line2["result"]["data"]["entity_id"]

        # Try to apply invalid constraint type
        response = tester.call_cli({
            "jsonrpc": "2.0",
            "method": "constraint.apply",
            "params": {
                "constraint_type": "invalid_type",
                "entity_ids": [line1_id, line2_id]
            },
            "id": 6
        })
        assert "error" in response, "Should get error for invalid constraint type"
        print(f"   Got expected error: {response['error']['message']}")

    tester.test("Error Handling", test_error_handling)

    # Test 7: Workspace operations
    def test_workspaces():
        import uuid
        workspace_name = f"test_ws_{uuid.uuid4().hex[:8]}"

        print(f"\n1. Creating workspace '{workspace_name}'...")
        create = tester.call_cli({
            "jsonrpc": "2.0",
            "method": "workspace.create",
            "params": {
                "workspace_name": workspace_name,
                "base_workspace_id": "main"
            },
            "id": 1
        })
        tester.assert_success(create, "Workspace create")
        workspace_id = create["result"]["data"]["workspace_id"]
        print(f"   Created workspace: {workspace_id}")

        print("\n2. Listing workspaces...")
        list_ws = tester.call_cli({
            "jsonrpc": "2.0",
            "method": "workspace.list",
            "params": {},
            "id": 2
        })
        tester.assert_success(list_ws, "Workspace list")
        workspaces = list_ws["result"]["data"]["workspaces"]
        print(f"   Total workspaces: {len(workspaces)}")
        assert any(ws["workspace_id"] == workspace_id for ws in workspaces)

        print("\n3. Getting workspace status...")
        status = tester.call_cli({
            "jsonrpc": "2.0",
            "method": "workspace.status",
            "params": {},
            "id": 3
        })
        tester.assert_success(status, "Workspace status")
        print(f"   Active workspace: {status['result']['data']['workspace_id']}")

    tester.test("Workspace Operations", test_workspaces)

    # Print final summary
    tester.print_summary()

    # Clean up test files
    import os
    for file in ["manual_test_export.json", "manual_test_export.stl"]:
        if os.path.exists(file):
            os.remove(file)
            print(f"\nCleaned up: {file}")

    return tester.fail_count == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
