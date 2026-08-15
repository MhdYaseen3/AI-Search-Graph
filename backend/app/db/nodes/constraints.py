"""Neo4j schema constraints and indexes for graph node models."""

NODE_CONSTRAINTS: tuple[str, ...] = (
    "CREATE CONSTRAINT candidate_id_unique IF NOT EXISTS "
    "FOR (c:Candidate) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT skill_name_unique IF NOT EXISTS "
    "FOR (s:Skill) REQUIRE s.name IS UNIQUE",
    "CREATE CONSTRAINT project_id_unique IF NOT EXISTS "
    "FOR (p:Project) REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT technology_name_unique IF NOT EXISTS "
    "FOR (t:Technology) REQUIRE t.name IS UNIQUE",
    "CREATE CONSTRAINT experience_id_unique IF NOT EXISTS "
    "FOR (e:Experience) REQUIRE e.id IS UNIQUE",
)

NODE_INDEXES: tuple[str, ...] = (
    "CREATE INDEX candidate_name_index IF NOT EXISTS "
    "FOR (c:Candidate) ON (c.full_name)",
    "CREATE INDEX skill_category_index IF NOT EXISTS "
    "FOR (s:Skill) ON (s.category)",
    "CREATE INDEX technology_category_index IF NOT EXISTS "
    "FOR (t:Technology) ON (t.category)",
)

SCHEMA_STATEMENTS: tuple[str, ...] = NODE_CONSTRAINTS + NODE_INDEXES
