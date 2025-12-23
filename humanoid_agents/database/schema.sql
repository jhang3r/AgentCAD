-- AgentCAD Humanoid Robot Design System Database Schema
-- Optimized for parallel agent access with proper locking

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Global Constraints Table
CREATE TABLE IF NOT EXISTS global_constraints (
    id SERIAL PRIMARY KEY,
    version INTEGER NOT NULL DEFAULT 1,
    total_mass_kg_max DECIMAL(10, 2) NOT NULL,
    total_cost_usd_max DECIMAL(10, 2) NOT NULL,
    height_m DECIMAL(10, 3) NOT NULL,
    voltage_v INTEGER NOT NULL,
    budget_allocations JSONB NOT NULL, -- {subsystem: {mass_kg, cost_usd, power_w}}
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create index on version for fast lookups
CREATE INDEX IF NOT EXISTS idx_global_constraints_version ON global_constraints(version DESC);

-- Subsystems Table
CREATE TABLE IF NOT EXISTS subsystems (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) UNIQUE NOT NULL,
    state VARCHAR(20) NOT NULL DEFAULT 'not_started', -- not_started, initializing, designing, validating, complete
    current_mass_kg DECIMAL(10, 3) DEFAULT 0,
    current_cost_usd DECIMAL(10, 2) DEFAULT 0,
    current_power_w DECIMAL(10, 2) DEFAULT 0,
    iteration INTEGER DEFAULT 0,
    within_budget BOOLEAN DEFAULT true,
    agent_version VARCHAR(50),
    last_agent_execution_id UUID,
    metadata JSONB, -- flexible field for subsystem-specific data
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_subsystems_name ON subsystems(name);
CREATE INDEX IF NOT EXISTS idx_subsystems_state ON subsystems(state);

-- Subsystem Requirements Table
CREATE TABLE IF NOT EXISTS subsystem_requirements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subsystem_name VARCHAR(50) NOT NULL REFERENCES subsystems(name) ON DELETE CASCADE,
    version INTEGER NOT NULL DEFAULT 1,
    requirements JSONB NOT NULL,
    created_by VARCHAR(50), -- which agent created this
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(subsystem_name, version)
);

CREATE INDEX IF NOT EXISTS idx_subsystem_requirements_name ON subsystem_requirements(subsystem_name);

-- Subsystem Interfaces Table (what each subsystem publishes for others)
CREATE TABLE IF NOT EXISTS subsystem_interfaces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subsystem_name VARCHAR(50) NOT NULL REFERENCES subsystems(name) ON DELETE CASCADE,
    version INTEGER NOT NULL DEFAULT 1,
    interfaces JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(subsystem_name, version)
);

CREATE INDEX IF NOT EXISTS idx_subsystem_interfaces_name ON subsystem_interfaces(subsystem_name);

-- Subsystem Designs Table (detailed design data)
CREATE TABLE IF NOT EXISTS subsystem_designs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subsystem_name VARCHAR(50) NOT NULL REFERENCES subsystems(name) ON DELETE CASCADE,
    version INTEGER NOT NULL DEFAULT 1,
    design_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(subsystem_name, version)
);

CREATE INDEX IF NOT EXISTS idx_subsystem_designs_name ON subsystem_designs(subsystem_name);

-- Conflicts Table
CREATE TABLE IF NOT EXISTS conflicts (
    id SERIAL PRIMARY KEY,
    conflict_id INTEGER UNIQUE NOT NULL,
    severity VARCHAR(20) NOT NULL, -- critical, high, medium, low
    priority INTEGER DEFAULT 3, -- 1=critical, 2=high, 3=medium, 4=low
    source_agent VARCHAR(50) NOT NULL,
    target_agent VARCHAR(50),
    description TEXT NOT NULL,
    details JSONB,
    status VARCHAR(20) NOT NULL DEFAULT 'open', -- open, resolving, resolved
    resolution TEXT,
    blocks_agents TEXT[], -- array of agent names that are blocked
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(50)
);

CREATE INDEX IF NOT EXISTS idx_conflicts_status ON conflicts(status);
CREATE INDEX IF NOT EXISTS idx_conflicts_priority ON conflicts(priority);
CREATE INDEX IF NOT EXISTS idx_conflicts_created_at ON conflicts(created_at DESC);

-- Agent Activity Logs Table
CREATE TABLE IF NOT EXISTS agent_activity_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_name VARCHAR(50) NOT NULL,
    activity VARCHAR(100) NOT NULL,
    details JSONB,
    execution_id UUID, -- links multiple activities from same agent execution
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_logs_agent ON agent_activity_logs(agent_name);
CREATE INDEX IF NOT EXISTS idx_agent_logs_timestamp ON agent_activity_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_agent_logs_execution ON agent_activity_logs(execution_id);

-- Agent Locks Table (for optimistic locking / coordination)
CREATE TABLE IF NOT EXISTS agent_locks (
    id SERIAL PRIMARY KEY,
    resource_type VARCHAR(50) NOT NULL, -- 'subsystem', 'conflict', 'global_constraints'
    resource_name VARCHAR(50) NOT NULL,
    locked_by VARCHAR(50) NOT NULL, -- agent name
    execution_id UUID NOT NULL,
    locked_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    UNIQUE(resource_type, resource_name)
);

CREATE INDEX IF NOT EXISTS idx_agent_locks_resource ON agent_locks(resource_type, resource_name);
CREATE INDEX IF NOT EXISTS idx_agent_locks_expires ON agent_locks(expires_at);

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at
CREATE TRIGGER update_global_constraints_updated_at BEFORE UPDATE ON global_constraints
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subsystems_updated_at BEFORE UPDATE ON subsystems
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subsystem_interfaces_updated_at BEFORE UPDATE ON subsystem_interfaces
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to clean up expired locks
CREATE OR REPLACE FUNCTION cleanup_expired_locks()
RETURNS void AS $$
BEGIN
    DELETE FROM agent_locks WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- Initialize subsystems
INSERT INTO subsystems (name, state) VALUES
    ('skeleton', 'not_started'),
    ('actuation', 'not_started'),
    ('power', 'not_started'),
    ('sensing', 'not_started'),
    ('shell', 'not_started'),
    ('integration', 'not_started'),
    ('system_architect', 'not_started')
ON CONFLICT (name) DO NOTHING;

-- Grant permissions (adjust as needed for security)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- CAD Geometry Storage - STEP files and component library
CREATE TABLE IF NOT EXISTS cad_components (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    component_name VARCHAR(100) NOT NULL,
    component_type VARCHAR(50) NOT NULL, -- 'bone', 'joint', 'motor_mount', 'gear', 'custom'
    subsystem_name VARCHAR(50) REFERENCES subsystems(name) ON DELETE CASCADE,
    version INTEGER NOT NULL DEFAULT 1,
    file_format VARCHAR(10) DEFAULT 'STEP', -- 'STEP', 'STL', 'IGES'
    geometry_data BYTEA NOT NULL, -- Binary STEP file data
    file_size_bytes INTEGER,
    metadata JSONB, -- {mass_kg, material, dimensions, bounding_box, etc}
    created_by VARCHAR(50), -- Agent that created this
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(component_name, version)
);

-- Indexes for CAD components
CREATE INDEX IF NOT EXISTS idx_cad_components_name ON cad_components(component_name);
CREATE INDEX IF NOT EXISTS idx_cad_components_type ON cad_components(component_type);
CREATE INDEX IF NOT EXISTS idx_cad_components_subsystem ON cad_components(subsystem_name);
CREATE INDEX IF NOT EXISTS idx_cad_components_version ON cad_components(component_name, version DESC);

-- CAD Assemblies - How components fit together
CREATE TABLE IF NOT EXISTS cad_assemblies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assembly_name VARCHAR(100) NOT NULL,
    subsystem_name VARCHAR(50) REFERENCES subsystems(name) ON DELETE CASCADE,
    version INTEGER NOT NULL DEFAULT 1,
    assembly_tree JSONB NOT NULL, -- Hierarchical structure of components with transforms
    created_by VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(assembly_name, version)
);

CREATE INDEX IF NOT EXISTS idx_cad_assemblies_name ON cad_assemblies(assembly_name);
CREATE INDEX IF NOT EXISTS idx_cad_assemblies_subsystem ON cad_assemblies(subsystem_name);

-- Component Relations - Mates, constraints between components
CREATE TABLE IF NOT EXISTS component_relations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    component_a_id UUID REFERENCES cad_components(id) ON DELETE CASCADE,
    component_b_id UUID REFERENCES cad_components(id) ON DELETE CASCADE,
    relation_type VARCHAR(50) NOT NULL, -- 'mate', 'fastener', 'weld', 'interference'
    relation_data JSONB, -- {type: 'concentric', axis, offset, etc}
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_component_relations_a ON component_relations(component_a_id);
CREATE INDEX IF NOT EXISTS idx_component_relations_b ON component_relations(component_b_id);

-- Component Library - Catalog of reusable parts (bearings, motors, fasteners)
CREATE TABLE IF NOT EXISTS component_library (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    part_number VARCHAR(100) UNIQUE NOT NULL,
    manufacturer VARCHAR(100),
    part_name VARCHAR(200) NOT NULL,
    category VARCHAR(50) NOT NULL, -- 'bearing', 'motor', 'fastener', 'sensor', 'battery'
    specifications JSONB NOT NULL, -- All specs: dimensions, ratings, etc
    geometry_id UUID REFERENCES cad_components(id), -- Link to CAD geometry
    cost_usd DECIMAL(10, 2),
    mass_kg DECIMAL(10, 5),
    lead_time_days INTEGER,
    datasheet_url TEXT,
    supplier_url TEXT,
    in_stock BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_component_library_category ON component_library(category);
CREATE INDEX IF NOT EXISTS idx_component_library_part_number ON component_library(part_number);

-- View for component statistics
CREATE OR REPLACE VIEW component_stats AS
SELECT
    subsystem_name,
    component_type,
    COUNT(*) as component_count,
    SUM(file_size_bytes) as total_size_bytes,
    AVG((metadata->>'mass_kg')::float) as avg_mass_kg
FROM cad_components
GROUP BY subsystem_name, component_type;

-- Create view for current system status
CREATE OR REPLACE VIEW system_status AS
SELECT
    s.name,
    s.state,
    s.current_mass_kg,
    s.current_cost_usd,
    s.current_power_w,
    s.within_budget,
    s.iteration,
    s.updated_at,
    COUNT(DISTINCT c.id) FILTER (WHERE c.status = 'open' AND (c.source_agent = s.name OR c.target_agent = s.name)) as active_conflicts,
    COUNT(DISTINCT cad.id) as cad_components_count
FROM subsystems s
LEFT JOIN conflicts c ON (c.source_agent = s.name OR c.target_agent = s.name) AND c.status = 'open'
LEFT JOIN cad_components cad ON cad.subsystem_name = s.name
GROUP BY s.id, s.name, s.state, s.current_mass_kg, s.current_cost_usd, s.current_power_w, s.within_budget, s.iteration, s.updated_at
ORDER BY s.name;
