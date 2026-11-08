"""Neo4j schema constraints and indexes for graph node models."""

NODE_CONSTRAINTS: tuple[str, ...] = (
    "CREATE CONSTRAINT candidate_id_unique IF NOT EXISTS "
    "FOR (c:Candidate) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT gmail_attachment_identity_unique IF NOT EXISTS "
    "FOR (a:GmailAttachment) REQUIRE (a.message_id, a.attachment_id) IS UNIQUE",
    "CREATE CONSTRAINT gmail_attachment_hash_unique IF NOT EXISTS "
    "FOR (h:GmailAttachmentHash) REQUIRE h.sha256 IS UNIQUE",
    "CREATE CONSTRAINT skill_name_unique IF NOT EXISTS "
    "FOR (s:Skill) REQUIRE s.name IS UNIQUE",
    "CREATE CONSTRAINT project_id_unique IF NOT EXISTS "
    "FOR (p:Project) REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT technology_name_unique IF NOT EXISTS "
    "FOR (t:Technology) REQUIRE t.name IS UNIQUE",
    "CREATE CONSTRAINT experience_id_unique IF NOT EXISTS "
    "FOR (e:Experience) REQUIRE e.id IS UNIQUE",
    "CREATE CONSTRAINT job_application_id_unique IF NOT EXISTS "
    "FOR (a:JobApplication) REQUIRE a.id IS UNIQUE",
)

NODE_INDEXES: tuple[str, ...] = (
    "CREATE INDEX candidate_name_index IF NOT EXISTS "
    "FOR (c:Candidate) ON (c.full_name)",
    "CREATE INDEX gmail_attachment_imported_at_index IF NOT EXISTS "
    "FOR (a:GmailAttachment) ON (a.imported_at)",
    "CREATE INDEX skill_category_index IF NOT EXISTS "
    "FOR (s:Skill) ON (s.category)",
    "CREATE INDEX technology_category_index IF NOT EXISTS "
    "FOR (t:Technology) ON (t.category)",
)

SCHEMA_MIGRATIONS: tuple[str, ...] = (
    """
    MATCH (a:GmailAttachment)
    WHERE a.status IS NULL OR a.source IS NULL OR a.imported_at IS NULL
    SET a.status = coalesce(
            a.status,
            CASE WHEN a.candidate_id IS NOT NULL THEN 'SUCCESS' ELSE 'FAILED' END
        ),
        a.source = coalesce(a.source, 'gmail'),
        a.imported_at = coalesce(
            a.imported_at,
            a.processed_at,
            toString(datetime())
        ),
        a.updated_at = coalesce(
            a.updated_at,
            a.processed_at,
            toString(datetime())
        )
    RETURN count(a) AS migrated
    """,
)

SCHEMA_STATEMENTS: tuple[str, ...] = (
    SCHEMA_MIGRATIONS + NODE_CONSTRAINTS + NODE_INDEXES
)
