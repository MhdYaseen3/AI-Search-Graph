"""Development-only cleanup for resume ingestion data.

This module provides a reset mechanism for development/test candidate data.
It is intentionally separate from the production DELETE API and includes
safeguards to:

1. Only run in development environments (blocked in production)
2. Preserve shared nodes (Skill, Technology) that are still referenced
3. Clean up candidate-owned nodes (Experience, Education, Project)
4. Remove uploaded resume files for deleted candidates
5. Require explicit manual invocation (never automatic)
"""

from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.core.exceptions import ValidationError
from app.db.neo4j import Neo4jConnection


# Node labels that are owned by a single candidate (no sharing across candidates)
CANDIDATE_OWNED_LABELS = (
    "Experience",
    "Education",
    "Project",
)

# Node labels that can be shared across multiple candidates/jobs
SHARED_LABELS = (
    "Skill",
    "Technology",
)


async def reset_development_resume_data(
    neo4j: Neo4jConnection,
    upload_dir: Path | None = None,
) -> dict[str, int]:
    """Remove all development candidate data and unreferenced shared entities.

    This function is intentionally separate from the production DELETE API.
    It only runs in a development environment and never deletes shared nodes
    that still have any graph relationship.

    Process:
    1. Collect all candidate IDs before deletion
    2. Delete all Candidate nodes and their relationships
    3. Delete candidate-owned nodes with no remaining relationships
    4. Delete shared nodes only if they have no relationships to any entity
    5. Remove uploaded resume files for deleted candidates

    Args:
        neo4j: Neo4j connection instance
        upload_dir: Optional custom upload directory path (defaults to settings.upload_dir)

    Returns:
        Dictionary with deletion counts:
        - candidates_deleted: number of Candidate nodes removed
        - orphan_nodes_deleted: number of orphaned nodes removed
        - files_deleted: number of uploaded files removed

    Raises:
        ValidationError: If called in production environment
    """
    if settings.is_production:
        raise ValidationError("Development reset is disabled in production")

    # Step 1: Collect all candidate IDs before deletion
    candidate_records = await neo4j.execute_read(
        "MATCH (c:Candidate) RETURN c.id AS candidate_id"
    )
    candidate_ids = [
        record["candidate_id"]
        for record in candidate_records
        if record.get("candidate_id")
    ]

    # Step 2: Delete all Candidate nodes (DETACH DELETE also removes relationships)
    deleted_candidates_records = await neo4j.execute_write(
        """
        MATCH (c:Candidate)
        DETACH DELETE c
        RETURN count(c) AS deleted
        """
    )
    deleted_candidates = (
        deleted_candidates_records[0].get("deleted", 0)
        if deleted_candidates_records
        else 0
    )

    # Step 3: Delete candidate-owned nodes that now have no relationships
    # These labels should only connect to Candidates, so after Candidate deletion,
    # any remaining nodes are orphaned and can be safely deleted
    deleted_orphans = 0
    for label in CANDIDATE_OWNED_LABELS:
        records = await neo4j.execute_write(
            f"""
            MATCH (n:{label})
            WHERE NOT (n)--()
            DETACH DELETE n
            RETURN count(n) AS deleted
            """
        )
        deleted_orphans += records[0].get("deleted", 0) if records else 0

    # Step 4: Delete shared nodes only if they have no relationships
    # These can be connected to Jobs or Projects, so we must preserve any
    # node that still has any relationship
    for label in SHARED_LABELS:
        records = await neo4j.execute_write(
            f"""
            MATCH (n:{label})
            WHERE NOT (n)--()
            DELETE n
            RETURN count(n) AS deleted
            """
        )
        deleted_orphans += records[0].get("deleted", 0) if records else 0

    # Step 5: Remove uploaded resume files for deleted candidates
    removed_files = _remove_candidate_uploads(
        candidate_ids,
        upload_dir or settings.upload_dir,
    )

    return {
        "candidates_deleted": deleted_candidates,
        "orphan_nodes_deleted": deleted_orphans,
        "files_deleted": removed_files,
    }


def _remove_candidate_uploads(candidate_ids: list[str], upload_dir: Path) -> int:
    """Remove uploaded resume files for deleted candidates.

    Files are matched by the pattern: {candidate_id}_{filename}

    Args:
        candidate_ids: List of candidate IDs to clean up
        upload_dir: Path to the upload directory

    Returns:
        Number of files successfully deleted
    """
    removed = 0
    if not upload_dir.exists():
        return removed

    for candidate_id in candidate_ids:
        for path in upload_dir.glob(f"{candidate_id}_*"):
            if path.is_file():
                path.unlink()
                removed += 1

    return removed