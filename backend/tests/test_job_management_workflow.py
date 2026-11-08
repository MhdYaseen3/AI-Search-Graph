from __future__ import annotations

from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_job_service, get_match_service
from app.main import app
from app.services.ai_match_explanation import AIMatchExplanationService
from app.services.job import JobManagementService
from app.services.match import MatchService


class FakeResult:
    def __init__(self, records: list[dict[str, Any]]):
        self.records = records

    async def data(self):
        return self.records

    async def consume(self):
        return None


class FakeTransaction:
    def __init__(self, database: FakeJobDatabase):
        self.database = database

    async def run(self, query: str, parameters: dict[str, Any] | None = None):
        params = parameters or {}
        if "MERGE (a:JobApplication" in query:
            job = self.database.jobs.get(params["job_id"])
            candidate = self.database.candidates.get(params["candidate_id"])
            if not job or not candidate:
                return FakeResult([])
            application = self.database.applications.setdefault(
                params["application_id"],
                {
                    "id": params["application_id"],
                    "job_id": params["job_id"],
                    "candidate_id": params["candidate_id"],
                    "status": "Applied",
                    "created_at": params["now"],
                    "updated_at": params["now"],
                },
            )
            return FakeResult([self.database.application_record(application)])
        return FakeResult([])


class FakeJobDatabase:
    def __init__(self):
        self.jobs: dict[str, dict[str, Any]] = {}
        self.applications: dict[str, dict[str, Any]] = {}
        self.candidates = {
            "candidate-1": {
                "id": "candidate-1",
                "full_name": "Jordan Lee",
                "email": "jordan@example.com",
                "summary": "Python engineer with GraphCV portfolio experience.",
                "skills": ["Python", "FastAPI"],
                "technologies": ["Neo4j"],
                "projects": ["GraphCV portfolio"],
                "education": [],
                "roles": ["Software Engineer"],
                "experiences": [
                    {
                        "company": "Example",
                        "role": "Software Engineer",
                        "start_date": "2019-01",
                        "end_date": None,
                    }
                ],
            },
            "candidate-2": {
                "id": "candidate-2",
                "full_name": "Taylor Smith",
                "email": "taylor@example.com",
                "summary": "Java developer.",
                "skills": ["Java"],
                "technologies": [],
                "projects": [],
                "education": [],
                "roles": [],
                "experiences": [],
            },
        }

    async def execute_write(self, query: str, parameters=None):
        params = parameters or {}
        if "MERGE (n:Job" in query:
            node = {
                **params["properties"],
                "id": params["id"],
                "created_at": params["created_at"],
                "updated_at": params["updated_at"],
            }
            self.jobs[node["id"]] = node
            return [{"n": node}]
        if "SET a.status = $status" in query:
            application = next(
                (
                    item
                    for item in self.applications.values()
                    if item["job_id"] == params["job_id"]
                    and item["candidate_id"] == params["candidate_id"]
                ),
                None,
            )
            if not application:
                return []
            application["status"] = params["status"]
            application["updated_at"] = params["now"]
            return [self.application_record(application)]
        return []

    async def execute_read(self, query: str, parameters=None):
        params = parameters or {}
        if "MATCH (j:Job {id: $job_id})-[:HAS_APPLICATION]" in query:
            return [
                self.application_record(application)
                for application in self.applications.values()
                if application["job_id"] == params["job_id"]
            ]
        if "MATCH (j:Job {id: $id})" in query:
            job = self.jobs.get(params["id"])
            return [{"n": job}] if job else []
        if "MATCH (j:Job {id: $job_id})" in query:
            job = self.jobs.get(params["job_id"])
            return [{"j": job}] if job else []
        if "MATCH (c:Candidate)" in query:
            return [self.search_record(candidate, params) for candidate in self.candidates.values()]
        if "MATCH (c:Candidate {id:" in query:
            candidate = self.candidates.get(params["candidate_id"])
            return [{"candidate_id": candidate["id"]}] if candidate else []
        return []

    async def execute_write_transaction(self, work):
        return await work(FakeTransaction(self))

    @staticmethod
    def application_record(application):
        return {
            **application,
            "full_name": "Jordan Lee",
            "email": "jordan@example.com",
            "summary": "Python engineer with GraphCV portfolio experience.",
        }

    @staticmethod
    def search_record(candidate, params):
        skills = candidate["skills"]
        technologies = candidate["technologies"]
        projects = candidate["projects"]

        def exact_matches(requested, options):
            return [
                item for item in requested
                if any(str(value).casefold() == str(item).casefold() for value in options)
            ]

        return {
            "candidate_id": candidate["id"],
            "full_name": candidate["full_name"],
            "summary": candidate["summary"],
            "skills": skills,
            "technologies": technologies,
            "projects": projects,
            "education": [],
            "roles": candidate["roles"],
            "experiences": candidate["experiences"],
            "matched_skills": exact_matches(params.get("skills", []), skills),
            "matched_technologies": exact_matches(
                params.get("technologies", []),
                technologies,
            ),
            "matched_projects": [
                project
                for project in params.get("projects", [])
                if any(
                    project.casefold() in candidate_project.casefold()
                    for candidate_project in projects
                )
            ],
            "matched_roles": [],
            "matched_education": [],
        }


class FakeAIExplanation(AIMatchExplanationService):
    async def generate_explanation(self, **kwargs):
        return "Candidate profile aligns with the required skills."


@pytest.mark.asyncio
async def test_job_crud_matching_and_applicant_workflow():
    database = FakeJobDatabase()
    app.dependency_overrides[get_job_service] = lambda: JobManagementService(database)
    app.dependency_overrides[get_match_service] = lambda: MatchService(
        database,
        FakeAIExplanation(),
    )
    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/api/v1/jobs",
                json={
                    "title": "Python Engineer",
                    "description": "Build GraphCV portfolio tools.",
                    "required_skills": ["Python", "FastAPI"],
                    "experience": 3,
                    "location": "Remote",
                    "employment_type": "Full-time",
                    "salary": "USD 100000 - 120000",
                    "status": "Active",
                },
            )
            assert created.status_code == 201
            job_id = created.json()["id"]

            details = await client.get(f"/api/v1/jobs/{job_id}")
            assert details.status_code == 200
            assert details.json()["title"] == "Python Engineer"
            assert details.json()["salary"] == "USD 100000 - 120000"

            edited = await client.put(
                f"/api/v1/jobs/{job_id}",
                json={"title": "Senior Python Engineer"},
            )
            assert edited.status_code == 200
            assert edited.json()["title"] == "Senior Python Engineer"

            matches = await client.post(f"/api/v1/jobs/{job_id}/match")
            assert matches.status_code == 200
            matched = matches.json()["matched_candidates"][0]
            assert matched["candidate_id"] == "candidate-1"
            assert matched["matched_skills"] == ["Python", "FastAPI"]
            assert matched["match_score"] > 0
            assert matched["explanation"]
            second_match = matches.json()["matched_candidates"][1]
            assert second_match["candidate_id"] == "candidate-2"
            assert second_match["missing_skills"] == ["Python", "FastAPI"]

            application_url = f"/api/v1/jobs/{job_id}/applicants"
            first = await client.post(
                application_url,
                json={"candidate_id": "candidate-1"},
            )
            repeated = await client.post(
                application_url,
                json={"candidate_id": "candidate-1"},
            )
            assert first.status_code == 201
            assert repeated.status_code == 201
            assert first.json()["id"] == repeated.json()["id"]
            assert len(database.applications) == 1

            stage = await client.patch(
                f"{application_url}/candidate-1",
                json={"status": "Interview"},
            )
            assert stage.status_code == 200
            assert stage.json()["status"] == "Interview"
            applicants = await client.get(application_url)
            assert applicants.status_code == 200
            assert len(applicants.json()) == 1

            closed = await client.put(
                f"/api/v1/jobs/{job_id}",
                json={"status": "Closed"},
            )
            reopened = await client.put(
                f"/api/v1/jobs/{job_id}",
                json={"status": "Active"},
            )
            assert closed.json()["status"] == "Closed"
            assert reopened.json()["status"] == "Active"
    finally:
        app.dependency_overrides.pop(get_job_service, None)
        app.dependency_overrides.pop(get_match_service, None)
