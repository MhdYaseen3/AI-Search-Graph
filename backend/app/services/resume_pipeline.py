"""
Resume processing pipeline orchestrator.

I don't have your actual upload-handling code, so this file provides a
standalone `process_resume()` that does the one missing step: persist
extracted entities to Neo4j and return them. If you already have a
`process_resume()` function elsewhere (e.g. in app/api/resumes.py, after
your existing PDF upload + text extraction + skill extraction steps),
merge the body below into it rather than importing this module — the
flow is intentionally laid out as plain, copyable steps.

Expected existing pipeline (per your notes):
    1. PDF upload                  -> already works
    2. Text extraction (PyMuPDF)   -> already works
    3. Skill extraction            -> already works

This adds:
    4. Full structured parse (skills/technologies/projects/education)
    5. Persist all of it to Neo4j via Neo4jGraphService
    6. Return extracted entities + graph write counts for the API response
"""

from __future__ import annotations

from typing import Any, Dict

from neo4j import Driver

from app.schemas.resume_parser import ParsedResume
from app.services.neo4j_graph_service import Neo4jGraphService
from app.services.resume_parser_service import ResumeParserService


def process_resume(candidate_id: str, raw_text: str, driver: Driver) -> Dict[str, Any]:
    """Parse raw resume text and persist all extracted entities to Neo4j.

    Args:
        candidate_id: ID of the (already-existing) Candidate node to link
            everything to. Must match whatever property your Candidate
            nodes are keyed by — see CANDIDATE_ID_PROPERTY in
            neo4j_graph_service.py if that's not `candidate_id`.
        raw_text: Raw resume text, e.g. from your existing PyMuPDF
            extraction step.
        driver: Your app's shared neo4j.Driver instance.

    Returns:
        A dict ready to hand back as the API response body:
            {
              "candidate_id": "...",
              "extracted_entities": {
                  "skills": [...],
                  "technologies": [...],
                  "projects": [{"title", "description", "raw_text"}, ...],
                  "education": [{"institution", "degree", "raw_text"}, ...]
              },
              "graph": {
                  "skills_linked": N, "projects_linked": N,
                  "education_linked": N, "technologies_linked": N
              }
            }
    """
    parser = ResumeParserService()
    parsed: ParsedResume = parser.parse(raw_text)

    graph_service = Neo4jGraphService(driver)
    graph_summary = graph_service.persist_resume_entities(candidate_id, parsed)

    return {
        "candidate_id": candidate_id,
        "extracted_entities": {
            "skills": parsed.skills,
            "technologies": parsed.technologies,
            "projects": [p.model_dump() for p in parsed.projects],
            "education": [e.model_dump() for e in parsed.education],
        },
        "graph": graph_summary,
    }
