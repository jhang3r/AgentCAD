"""Agent Role Templates and Task Definitions.

Provides specialized prompts and task structures for different agent roles.
"""
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class AgentPromptTemplate:
    """Template for agent role with specific capabilities and constraints."""
    role: str
    description: str
    capabilities: List[str]
    constraints: List[str]
    example_tasks: List[str]


# ============================================================================
# AGENT ROLE DEFINITIONS
# ============================================================================

DESIGNER_AGENT = AgentPromptTemplate(
    role="designer",
    description="Creates 2D sketches and defines geometric intent",
    capabilities=[
        "Create points, lines, and circles",
        "Define dimensions and proportions",
        "Establish design intent",
        "Create closed sketches for extrusion"
    ],
    constraints=[
        "No solid modeling (extrude/boolean)",
        "Work in 2D space only",
        "Must create closed geometries for manufacturability",
        "All dimensions must be within bounds [-1e6, 1e6]"
    ],
    example_tasks=[
        "Create a rectangular base 100x80mm",
        "Design mounting hole pattern: 4 holes at corners, 5mm diameter",
        "Sketch a circular flange with 50mm outer diameter, 30mm inner diameter"
    ]
)

MODELER_AGENT = AgentPromptTemplate(
    role="modeler",
    description="Converts 2D sketches into 3D solids",
    capabilities=[
        "Extrude 2D sketches to create solids",
        "Perform boolean operations (union, subtract, intersect)",
        "Calculate volumes and surface areas",
        "Validate topology (manifold, closed shells)"
    ],
    constraints=[
        "Can only extrude closed sketches",
        "Extrusion distance must be positive",
        "Boolean operations require valid solid inputs",
        "Must verify topology after each operation"
    ],
    example_tasks=[
        "Extrude base sketch to 20mm height",
        "Union two overlapping parts into single solid",
        "Subtract mounting hole cylinders from base plate"
    ]
)

CONSTRAINT_AGENT = AgentPromptTemplate(
    role="constraint_solver",
    description="Applies and validates geometric constraints",
    capabilities=[
        "Apply parallel, perpendicular, coincident constraints",
        "Apply distance, angle, radius constraints",
        "Check constraint satisfaction",
        "Detect and resolve conflicts"
    ],
    constraints=[
        "Can only constrain existing entities",
        "Must check for constraint conflicts before applying",
        "Distance/angle constraints must have positive values",
        "Cannot over-constrain geometry"
    ],
    example_tasks=[
        "Ensure all edges perpendicular in rectangular frame",
        "Constrain hole spacing to exactly 50mm",
        "Verify all mounting holes have 5mm radius"
    ]
)

VALIDATOR_AGENT = AgentPromptTemplate(
    role="validator",
    description="Performs quality control and verification",
    capabilities=[
        "Query entity properties (volume, area, dimensions)",
        "Run validation scenarios",
        "Check topology validity",
        "Verify design requirements met"
    ],
    constraints=[
        "Read-only access (no modifications)",
        "Can query but not create entities",
        "Must report all violations found",
        "Cannot approve designs with errors"
    ],
    example_tasks=[
        "Verify total volume < 50000 mm^3",
        "Check all solids are manifold and closed",
        "Ensure no degenerate geometry (zero-length lines, etc)",
        "Validate mounting hole pattern matches specification"
    ]
)

OPTIMIZER_AGENT = AgentPromptTemplate(
    role="optimizer",
    description="Improves designs for specific objectives",
    capabilities=[
        "Analyze current design metrics",
        "Suggest geometry modifications",
        "Reduce material usage",
        "Simplify complexity"
    ],
    constraints=[
        "Must preserve design intent",
        "Cannot violate functional requirements",
        "All changes must improve objective function",
        "Must document all modifications"
    ],
    example_tasks=[
        "Reduce volume by 20% while maintaining strength",
        "Minimize surface area for coating cost reduction",
        "Simplify geometry from 50 entities to <30 entities"
    ]
)

INTEGRATOR_AGENT = AgentPromptTemplate(
    role="integrator",
    description="Merges work from multiple agents into final assembly",
    capabilities=[
        "Merge workspaces",
        "Detect and resolve conflicts",
        "Coordinate multi-agent work",
        "Export final assemblies"
    ],
    constraints=[
        "Must verify all parts before merging",
        "Cannot merge workspaces with validation errors",
        "Must resolve all conflicts before final export",
        "Maintains change history"
    ],
    example_tasks=[
        "Merge housing, lid, and internals into assembly",
        "Resolve overlapping geometry conflicts",
        "Export final assembly to STL for 3D printing"
    ]
)


# ============================================================================
# COLLABORATIVE TASK SCENARIOS
# ============================================================================

class CollaborativeScenario:
    """Defines a multi-agent collaborative task."""

    @staticmethod
    def simple_box_assembly() -> Dict[str, Any]:
        """Simple box assembly (already implemented in controller)."""
        return {
            "name": "Simple Box Assembly",
            "description": "4 agents build enclosure with housing, lid, and supports",
            "agents": [
                {"id": "housing", "role": "designer", "task": "Create base box 50x50x30mm"},
                {"id": "lid", "role": "designer", "task": "Create lid 50x50x5mm"},
                {"id": "support", "role": "modeler", "task": "Create mounting posts"},
                {"id": "integrator", "role": "integrator", "task": "Merge all parts"}
            ],
            "success_criteria": {
                "total_solids": 3,
                "no_conflicts": True,
                "all_manifold": True
            }
        }

    @staticmethod
    def mechanical_assembly() -> Dict[str, Any]:
        """Complex mechanical assembly with constraints."""
        return {
            "name": "Mechanical Assembly",
            "description": "Bracket with constrained mounting holes",
            "agents": [
                {"id": "designer", "role": "designer", "task": "Create L-bracket outline"},
                {"id": "constraint", "role": "constraint_solver", "task": "Apply perpendicular constraints"},
                {"id": "modeler", "role": "modeler", "task": "Extrude and add mounting holes"},
                {"id": "validator", "role": "validator", "task": "Verify dimensions and topology"},
                {"id": "integrator", "role": "integrator", "task": "Export final part"}
            ],
            "success_criteria": {
                "total_solids": 1,
                "constraints_satisfied": True,
                "volume_range": [1000, 5000],
                "all_manifold": True
            }
        }

    @staticmethod
    def design_competition() -> Dict[str, Any]:
        """3 agents compete to design optimal bracket."""
        return {
            "name": "Design Competition",
            "description": "3 agents compete for lightest bracket meeting requirements",
            "agents": [
                {"id": "agent_a", "role": "designer", "strategy": "solid_design"},
                {"id": "agent_b", "role": "designer", "strategy": "hollow_design"},
                {"id": "agent_c", "role": "designer", "strategy": "lattice_design"},
                {"id": "validator", "role": "validator", "task": "Verify all meet requirements"},
                {"id": "judge", "role": "integrator", "task": "Select winner (lowest volume)"}
            ],
            "success_criteria": {
                "min_volume": 0,  # Lower is better
                "strength_verified": True,
                "winner_selected": True
            }
        }

    @staticmethod
    def iterative_learning() -> Dict[str, Any]:
        """Single agent learns through iterations."""
        return {
            "name": "Iterative Learning",
            "description": "Agent improves box design over 10 iterations",
            "agents": [
                {"id": "learner", "role": "designer", "iterations": 10}
            ],
            "success_criteria": {
                "error_reduction": 50,  # % reduction
                "final_accuracy": 0.95,  # 95% success rate
                "learning_status": "good_learning"
            }
        }

    @staticmethod
    def review_feedback_loop() -> Dict[str, Any]:
        """Designer and reviewer iterate until approved."""
        return {
            "name": "Review & Feedback Loop",
            "description": "Designer creates, reviewer provides feedback, iterate",
            "agents": [
                {"id": "designer", "role": "designer"},
                {"id": "reviewer", "role": "validator"}
            ],
            "workflow": [
                {"step": 1, "agent": "designer", "action": "Create initial design"},
                {"step": 2, "agent": "reviewer", "action": "Validate and provide feedback"},
                {"step": 3, "agent": "designer", "action": "Revise based on feedback"},
                {"step": 4, "agent": "reviewer", "action": "Re-validate"},
                {"repeat": "until approved or max 5 iterations"}
            ],
            "success_criteria": {
                "reviewer_approved": True,
                "max_iterations": 5
            }
        }


# ============================================================================
# TASK DECOMPOSITION STRATEGIES
# ============================================================================

class TaskDecomposition:
    """Strategies for breaking down complex tasks."""

    @staticmethod
    def by_geometry_type():
        """Decompose by type of geometry."""
        return {
            "2d_geometry": ["designer"],
            "3d_solids": ["modeler"],
            "constraints": ["constraint_solver"],
            "validation": ["validator"]
        }

    @staticmethod
    def by_component():
        """Decompose by physical component."""
        return {
            "base_plate": ["designer", "modeler"],
            "mounting_bracket": ["designer", "modeler"],
            "fasteners": ["designer", "modeler"],
            "assembly": ["integrator"]
        }

    @staticmethod
    def by_pipeline_stage():
        """Decompose by design pipeline stage."""
        return {
            "stage_1_sketch": ["designer"],
            "stage_2_constraints": ["constraint_solver"],
            "stage_3_modeling": ["modeler"],
            "stage_4_validation": ["validator"],
            "stage_5_optimization": ["optimizer"],
            "stage_6_export": ["integrator"]
        }


# ============================================================================
# AGENT COORDINATION PATTERNS
# ============================================================================

class CoordinationPattern:
    """Common patterns for agent coordination."""

    SEQUENTIAL = "sequential"  # Agents work one after another
    PARALLEL = "parallel"  # Agents work simultaneously
    ITERATIVE = "iterative"  # Agents work in feedback loops
    COMPETITIVE = "competitive"  # Agents compete for best solution
    COLLABORATIVE = "collaborative"  # Agents share workspace

    @staticmethod
    def get_pattern_description(pattern: str) -> str:
        """Get description of coordination pattern."""
        descriptions = {
            "sequential": "Agents work in sequence, each building on previous work",
            "parallel": "Agents work simultaneously in isolated workspaces",
            "iterative": "Agents provide feedback to each other in loops",
            "competitive": "Agents compete to find best solution",
            "collaborative": "Agents share workspace and coordinate changes"
        }
        return descriptions.get(pattern, "Unknown pattern")


# ============================================================================
# AGENT PROMPT GENERATORS
# ============================================================================

def generate_agent_prompt(role: str, task: str, context: Dict[str, Any]) -> str:
    """Generate a detailed prompt for an agent.

    Args:
        role: Agent role (designer, modeler, etc.)
        task: Specific task description
        context: Additional context (workspace, constraints, etc.)

    Returns:
        Formatted prompt for the agent
    """
    templates = {
        "designer": DESIGNER_AGENT,
        "modeler": MODELER_AGENT,
        "constraint_solver": CONSTRAINT_AGENT,
        "validator": VALIDATOR_AGENT,
        "optimizer": OPTIMIZER_AGENT,
        "integrator": INTEGRATOR_AGENT
    }

    template = templates.get(role)
    if not template:
        return f"Unknown role: {role}"

    prompt = f"""
# Agent Role: {template.role.upper()}

## Description
{template.description}

## Your Task
{task}

## Your Capabilities
{chr(10).join(f"- {cap}" for cap in template.capabilities)}

## Constraints (You MUST follow these)
{chr(10).join(f"- {con}" for con in template.constraints)}

## Context
- Workspace: {context.get('workspace', 'main')}
- Available Entities: {context.get('entity_count', 0)}
- Collaboration Mode: {context.get('mode', 'independent')}

## Example Similar Tasks
{chr(10).join(f"{i+1}. {task}" for i, task in enumerate(template.example_tasks[:3]))}

## Instructions
1. Use JSON-RPC commands via the CLI interface
2. Work within your assigned workspace
3. Follow all constraints strictly
4. Document your operations
5. Report results when complete

Begin your task now.
"""
    return prompt.strip()


if __name__ == "__main__":
    # Demo: Print all agent role templates
    print("="*80)
    print("AGENT ROLE TEMPLATES")
    print("="*80)

    for template in [DESIGNER_AGENT, MODELER_AGENT, CONSTRAINT_AGENT,
                     VALIDATOR_AGENT, OPTIMIZER_AGENT, INTEGRATOR_AGENT]:
        print(f"\n{template.role.upper()}")
        print("-" * 80)
        print(f"Description: {template.description}")
        print(f"\nCapabilities:")
        for cap in template.capabilities:
            print(f"  - {cap}")
        print(f"\nConstraints:")
        for con in template.constraints:
            print(f"  - {con}")

    # Demo: Generate a sample prompt
    print("\n" + "="*80)
    print("SAMPLE AGENT PROMPT")
    print("="*80)
    prompt = generate_agent_prompt(
        role="designer",
        task="Create a rectangular mounting bracket 100x80mm with 4 corner holes",
        context={"workspace": "designer_ws", "entity_count": 0, "mode": "collaborative"}
    )
    print(prompt)
