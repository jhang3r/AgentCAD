"""Constraint graph representation and management.

The constraint graph represents entities as nodes and constraints as edges,
enabling constraint solving and conflict detection.
"""
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ConstraintGraph:
    """Graph representation of entities and constraints.

    Nodes represent geometric entities, edges represent constraints.
    """

    workspace_id: str
    entities: dict[str, Any] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)
    entity_constraints: dict[str, list[str]] = field(default_factory=dict)

    def add_entity(self, entity: Any) -> None:
        """Add entity to graph.

        Args:
            entity: Geometric entity to add
        """
        self.entities[entity.entity_id] = entity
        if entity.entity_id not in self.entity_constraints:
            self.entity_constraints[entity.entity_id] = []

    def add_constraint(self, constraint: Any) -> None:
        """Add constraint to graph.

        Args:
            constraint: Constraint to add
        """
        self.constraints[constraint.constraint_id] = constraint

        # Link constraint to its entities
        for entity_id in constraint.entity_ids:
            if entity_id not in self.entity_constraints:
                self.entity_constraints[entity_id] = []
            self.entity_constraints[entity_id].append(constraint.constraint_id)

    def get_entity(self, entity_id: str) -> Optional[Any]:
        """Get entity by ID.

        Args:
            entity_id: Entity identifier

        Returns:
            Entity or None if not found
        """
        return self.entities.get(entity_id)

    def get_constraint(self, constraint_id: str) -> Optional[Any]:
        """Get constraint by ID.

        Args:
            constraint_id: Constraint identifier

        Returns:
            Constraint or None if not found
        """
        return self.constraints.get(constraint_id)

    def get_constraints_for_entity(self, entity_id: str) -> list[Any]:
        """Get all constraints affecting an entity.

        Args:
            entity_id: Entity identifier

        Returns:
            List of constraints
        """
        constraint_ids = self.entity_constraints.get(entity_id, [])
        return [self.constraints[cid] for cid in constraint_ids if cid in self.constraints]

    def check_conflict(self, new_constraint: Any) -> tuple[bool, Optional[str]]:
        """Check if new constraint conflicts with existing constraints.

        Args:
            new_constraint: Constraint to check

        Returns:
            Tuple of (has_conflict, conflicting_constraint_id)
        """
        # Get constraints on the same entities
        affected_entity_ids = set(new_constraint.entity_ids)

        for constraint_id, constraint in self.constraints.items():
            constraint_entities = set(constraint.entity_ids)

            # Check if constraints share entities
            if constraint_entities == affected_entity_ids:
                # Same entities - check for logical conflicts
                if self._are_constraints_conflicting(new_constraint, constraint):
                    return True, constraint_id

        return False, None

    def _are_constraints_conflicting(self, constraint1: Any, constraint2: Any) -> bool:
        """Check if two constraints are logically conflicting.

        Args:
            constraint1: First constraint
            constraint2: Second constraint

        Returns:
            True if constraints conflict
        """
        # Parallel and perpendicular on same lines are conflicting
        if {constraint1.constraint_type, constraint2.constraint_type} == {"parallel", "perpendicular"}:
            return True

        # Multiple different distance constraints on same entities conflict
        if constraint1.constraint_type == "distance" and constraint2.constraint_type == "distance":
            if hasattr(constraint1, 'target_distance') and hasattr(constraint2, 'target_distance'):
                if abs(constraint1.target_distance - constraint2.target_distance) > 1e-6:
                    return True

        # Multiple different angle constraints on same entities conflict
        if constraint1.constraint_type == "angle" and constraint2.constraint_type == "angle":
            if hasattr(constraint1, 'target_angle') and hasattr(constraint2, 'target_angle'):
                if abs(constraint1.target_angle - constraint2.target_angle) > 1e-6:
                    return True

        return False

    def update_constraint_status(self) -> None:
        """Update satisfaction status for all constraints."""
        for constraint in self.constraints.values():
            is_satisfied, _ = constraint.check_satisfaction()
            constraint.satisfaction_status = "satisfied" if is_satisfied else "violated"

    def count_degrees_of_freedom(self) -> dict[str, int]:
        """Count degrees of freedom in the system.

        Returns:
            Dictionary with DOF statistics
        """
        # Simple DOF calculation
        # Each 2D point has 2 DOF, each 2D line has 4 DOF (2 points)
        total_dof = 0

        for entity in self.entities.values():
            if entity.entity_type == "point":
                total_dof += 2  # x, y
            elif entity.entity_type == "line":
                total_dof += 4  # start.x, start.y, end.x, end.y
            elif entity.entity_type == "circle":
                total_dof += 3  # center.x, center.y, radius

        # Each constraint removes DOF
        constrained_dof = len(self.constraints)

        return {
            "total_dof": total_dof,
            "constrained_dof": constrained_dof,
            "remaining_dof": max(0, total_dof - constrained_dof)
        }
