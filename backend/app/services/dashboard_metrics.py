import asyncio
import math
from typing import Any

from app.db.neo4j import Neo4jConnection
from app.schemas.dashboard import DashboardStatsResponse, ProcessingQueueMetrics
from app.services.match import MatchService

class DashboardMetricsService:
    """Build dashboard metrics from persisted graph data and live job matches."""

    def __init__(
        self,
        neo4j: Neo4jConnection,
        match_service: MatchService,
    ) -> None:
        self.neo4j = neo4j
        self.match_service = match_service

    async def get_stats(self) -> DashboardStatsResponse:
        (
            candidate_records,
            relationship_records,
            queue_records,
            job_records,
            recent_candidate_records,
            top_skill_records,
        ) = await asyncio.gather(
            self.neo4j.execute_read("MATCH (c:Candidate) RETURN count(c) AS total"),
            self.neo4j.execute_read("MATCH ()-[r]->() RETURN count(r) AS total"),
            self.neo4j.execute_read(
                """
            MATCH (a:GmailAttachment)
            WITH CASE
                WHEN a.status IS NOT NULL THEN a.status
                WHEN a.candidate_id IS NOT NULL THEN 'SUCCESS'
                ELSE 'FAILED'
            END AS status
            RETURN
                sum(CASE WHEN status = 'PENDING' THEN 1 ELSE 0 END) AS pending,
                sum(CASE WHEN status = 'PROCESSING' THEN 1 ELSE 0 END) AS processing,
                sum(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) AS completed,
                sum(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) AS failed,
                sum(CASE WHEN status = 'DUPLICATE' THEN 1 ELSE 0 END) AS duplicates
            """
            ),
            self.neo4j.execute_read(
                """
            MATCH (j:Job)
            WHERE j.status = 'Active'
            RETURN j.id AS job_id
            ORDER BY j.id
            """
            ),
            self.neo4j.execute_read(
                """
            MATCH (c:Candidate)
            OPTIONAL MATCH (c)-[r]-()
            RETURN c.id AS id,
                   c.full_name AS full_name,
                   c.location AS location,
                   c.created_at AS created_at,
                   count(DISTINCT r) AS relationship_count
            ORDER BY created_at DESC
            LIMIT 3
            """
            ),
            self.neo4j.execute_read(
                """
            MATCH (c:Candidate)-[:HAS_SKILL]->(s:Skill)
            RETURN s.name AS name, count(DISTINCT c) AS count
            ORDER BY count DESC, name
            LIMIT 5
            """
            ),
        )

        candidate_count = self._count(candidate_records)
        relationship_count = self._count(relationship_records)
        queue_data = queue_records[0] if queue_records else {}
        pending = int(queue_data.get("pending") or 0)
        processing = int(queue_data.get("processing") or 0)
        queue = ProcessingQueueMetrics(
            pending=pending,
            processing=processing,
            completed=int(queue_data.get("completed") or 0),
            failed=int(queue_data.get("failed") or 0),
            duplicates=int(queue_data.get("duplicates") or 0),
            idle=pending == 0 and processing == 0,
        )

        scores: list[float] = []
        for job_record in job_records:
            job_id = job_record.get("job_id")
            if not job_id:
                continue
            skip = 0
            while True:
                matches = await self.match_service.match_candidates(
                    job_id,
                    skip=skip,
                    generate_explanations=False,
                )
                if matches.total_candidates == 0:
                    break
                for candidate in matches.matched_candidates:
                    score = candidate.match_score
                    if math.isfinite(score) and 0 <= score <= 100:
                        scores.append(score)
                skip += matches.total_candidates

        average_score = round(sum(scores) / len(scores), 1) if scores else None
        return DashboardStatsResponse(
            total_resumes=candidate_count,
            graph_relationships=relationship_count,
            average_match_score=average_score,
            processing_queue=queue,
            recent_candidates=recent_candidate_records,
            top_skills=top_skill_records,
        )

    @staticmethod
    def _count(records: list[dict[str, Any]]) -> int:
        return int(records[0].get("total") or 0) if records else 0
