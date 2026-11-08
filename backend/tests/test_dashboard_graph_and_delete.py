from __future__ import annotations

from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_candidate_graph_service, get_candidate_service
from app.core.exceptions import NotFoundError
from app.main import app
from app.schemas.match import JobMatchResponse, MatchedCandidate
from app.services.candidate_graph import CandidateGraphService
from app.services.dashboard_metrics import DashboardMetricsService
from app.services.neo4j_graph import Neo4jGraphService


class FakeNeo4j:
    def __init__(self) -> None:
        self.write_query = ""
        self.write_result: list[dict[str, Any]] = [{"deleted": 1}]

    async def execute_read(self, query: str, parameters=None):
        params = parameters or {}
        if "count(c) AS total" in query:
            return [{"total": 3}]
        if "count(r) AS total" in query:
            return [{"total": 7}]
        if "GmailAttachment" in query:
            return [{
                "pending": 1,
                "processing": 2,
                "completed": 4,
                "failed": 1,
                "duplicates": 2,
            }]
        if "MATCH (j:Job)" in query:
            return [{"job_id": "job-1"}, {"job_id": "job-2"}]
        if "RETURN c.id AS candidate_id" in query:
            return [{
                "candidate_id": "candidate-1",
                "candidate_name": "Alex Candidate",
                "related": [{
                    "relationship_id": "rel-1",
                    "relationship": "HAS_SKILL",
                    "source_labels": ["Candidate"],
                    "source_properties": {
                        "id": "candidate-1",
                        "full_name": "Alex Candidate",
                    },
                    "target_labels": ["Skill"],
                    "target_properties": {"name": "Python"},
                }],
            }]
        return []

    async def execute_write(self, query: str, parameters=None):
        self.write_query = query
        return self.write_result


class FakeMatchService:
    async def match_candidates(
        self,
        job_id: str,
        *,
        skip: int = 0,
        generate_explanations: bool = True,
    ) -> JobMatchResponse:
        assert generate_explanations is False
        if skip:
            return JobMatchResponse(job_id=job_id, total_candidates=0)
        if job_id == "job-1":
            scores = [80.0, 60.0]
        else:
            scores = [100.0]
        return JobMatchResponse(
            job_id=job_id,
            total_candidates=len(scores),
            matched_candidates=[
                MatchedCandidate(
                    candidate_id=f"{job_id}-{index}",
                    full_name="Candidate",
                    match_score=score,
                    experience=0,
                )
                for index, score in enumerate(scores)
            ],
        )


@pytest.mark.asyncio
async def test_dashboard_metrics_use_persisted_counts_and_match_results():
    stats = await DashboardMetricsService(
        FakeNeo4j(),
        FakeMatchService(),
    ).get_stats()

    assert stats.total_resumes == 3
    assert stats.graph_relationships == 7
    assert stats.average_match_score == 80.0
    assert stats.processing_queue.pending == 1
    assert stats.processing_queue.processing == 2
    assert stats.processing_queue.completed == 4
    assert stats.processing_queue.failed == 1
    assert stats.processing_queue.duplicates == 2
    assert stats.processing_queue.idle is False


@pytest.mark.asyncio
async def test_dashboard_average_is_none_without_jobs_or_match_results():
    class NoJobsNeo4j(FakeNeo4j):
        async def execute_read(self, query: str, parameters=None):
            if "MATCH (j:Job)" in query:
                return []
            return await super().execute_read(query, parameters)

    stats = await DashboardMetricsService(
        NoJobsNeo4j(),
        FakeMatchService(),
    ).get_stats()

    assert stats.average_match_score is None


@pytest.mark.asyncio
async def test_global_graph_page_uses_real_candidate_relationships():
    graph = await CandidateGraphService(FakeNeo4j()).get_global_candidate_graph(
        skip=0,
        limit=1,
    )

    assert graph.total == 3
    assert graph.skip == 0
    assert graph.limit == 1
    assert {node.id for node in graph.nodes} == {"candidate-1", "skill-python"}
    assert [
        (link.source, link.target, link.type) for link in graph.links
    ] == [("candidate-1", "skill-python", "HAS_SKILL")]


@pytest.mark.asyncio
async def test_candidate_delete_removes_only_candidate_and_its_edges():
    neo4j = FakeNeo4j()
    await Neo4jGraphService(neo4j).delete_candidate("candidate-1")

    assert "MATCH (c:Candidate {id: $candidate_id})" in neo4j.write_query
    assert "DETACH DELETE c" in neo4j.write_query
    assert "DELETE n" not in neo4j.write_query


@pytest.mark.asyncio
async def test_candidate_delete_reports_missing_candidate():
    neo4j = FakeNeo4j()
    neo4j.write_result = [{"deleted": 0}]

    with pytest.raises(NotFoundError):
        await Neo4jGraphService(neo4j).delete_candidate("missing")


@pytest.mark.asyncio
async def test_global_graph_endpoint_is_registered_before_candidate_id_route():
    app.dependency_overrides[get_candidate_graph_service] = lambda: CandidateGraphService(
        FakeNeo4j()
    )
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/v1/candidates/graph",
                params={"skip": 0, "limit": 1},
            )
        assert response.status_code == 200
        assert response.json()["total"] == 3
        assert response.json()["links"][0]["type"] == "HAS_SKILL"
    finally:
        app.dependency_overrides.pop(get_candidate_graph_service, None)


@pytest.mark.asyncio
async def test_candidate_delete_endpoint_returns_not_found_for_missing_candidate():
    class MissingCandidateService:
        async def delete(self, candidate_id: str) -> None:
            raise NotFoundError(f"Candidate {candidate_id} not found")

    app.dependency_overrides[get_candidate_service] = MissingCandidateService
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.delete("/api/v1/candidates/missing")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(get_candidate_service, None)


@pytest.mark.asyncio
async def test_candidate_delete_endpoint_returns_success_after_service_deletion():
    class DeletingCandidateService:
        async def delete(self, candidate_id: str) -> None:
            self.deleted_id = candidate_id

    app.dependency_overrides[get_candidate_service] = DeletingCandidateService
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.delete("/api/v1/candidates/candidate-1")
        assert response.status_code == 200
        assert response.json()["message"] == "Candidate candidate-1 deleted"
    finally:
        app.dependency_overrides.pop(get_candidate_service, None)
