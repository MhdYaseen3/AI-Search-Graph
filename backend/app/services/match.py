import logging

from app.core.exceptions import NotFoundError
from app.db.neo4j import Neo4jConnection
from app.db.nodes import JobNode
from app.schemas.match import JobMatchResponse, MatchedCandidate
from app.services.ai_match_explanation import AIMatchExplanationService
from app.services.query_parser import QueryParser
from app.services.ranking import RankingService
from app.services.search import SearchService

logger = logging.getLogger(__name__)


class MatchService:
    """Rank the existing candidate graph against a saved job."""

    def __init__(
        self,
        neo4j: Neo4jConnection,
        ai_explanation_service: AIMatchExplanationService,
    ) -> None:
        self.neo4j = neo4j
        self.ai_explanation_service = ai_explanation_service
        self.search_service = SearchService(neo4j)
        self.ranking_service = RankingService()
        self.query_parser = QueryParser()

    async def match_candidates(
        self,
        job_id: str,
        *,
        skip: int = 0,
        generate_explanations: bool = True,
    ) -> JobMatchResponse:
        job_records = await self.neo4j.execute_read(
            "MATCH (j:Job {id: $job_id}) RETURN j",
            {"job_id": job_id},
        )
        if not job_records:
            raise NotFoundError(f"Job {job_id} not found")

        job = JobNode.from_neo4j(job_records[0]["j"]).to_domain()
        query_text = " ".join(
            [
                job.title,
                job.description,
                *job.required_skills,
                f"{job.experience} years experience",
            ]
        )
        query = self.query_parser.parse(query_text, limit=100)
        query.skills = list(dict.fromkeys([*job.required_skills, *query.skills]))
        candidates = await self.search_service.search(
            query,
            include_nonmatching=True,
            skip=skip,
        )

        for candidate in candidates:
            available_skills = {
                str(skill).casefold()
                for skill in [
                    *candidate.get("skills", []),
                    *candidate.get("technologies", []),
                ]
            }
            candidate["matched_skills"] = [
                skill for skill in job.required_skills
                if skill.casefold() in available_skills
            ]
            candidate["missing_skills"] = [
                skill for skill in job.required_skills
                if skill.casefold() not in available_skills
            ]
            projects = [
                str(project)
                for project in candidate.get("projects", [])
                if project
            ]
            candidate["matched_projects"] = [
                project
                for project in query.projects
                if any(project.casefold() in item.casefold() for item in projects)
            ]
            candidate["missing_projects"] = [
                project
                for project in query.projects
                if project not in candidate["matched_projects"]
            ]

        ranked = self.ranking_service.rank(candidates, query)
        candidates_by_id = {
            candidate["candidate_id"]: candidate for candidate in candidates
        }
        matches = []
        for item in ranked:
            candidate = candidates_by_id[item.candidate_id]
            experience_years = candidate.get("experience_years")
            explanation_parts = [
                (
                    "Matched skills: " + ", ".join(candidate["matched_skills"])
                    if candidate["matched_skills"]
                    else "No required skills matched"
                ),
                (
                    f"Experience: {experience_years or 0:g} years "
                    f"(required {job.experience}+)"
                ),
            ]
            if query.projects:
                explanation_parts.append(
                    "Matched projects: "
                    + (", ".join(candidate["matched_projects"]) or "none")
                )
            explanation = ". ".join(explanation_parts)
            match_score = item.score * 100
            ai_explanation = None
            if generate_explanations:
                try:
                    ai_explanation = await self.ai_explanation_service.generate_explanation(
                        job_title=job.title,
                        matched_skills=candidate["matched_skills"],
                        missing_skills=candidate["missing_skills"],
                        match_score=match_score,
                        recommendation=self.get_match_recommendation(match_score),
                    )
                except Exception:
                    logger.exception("Failed to generate AI match explanation")

            matches.append(
                MatchedCandidate(
                    candidate_id=item.candidate_id,
                    full_name=item.full_name,
                    match_score=match_score,
                    matched_skills=candidate["matched_skills"],
                    missing_skills=candidate["missing_skills"],
                    matched_projects=candidate["matched_projects"],
                    missing_projects=candidate["missing_projects"],
                    experience=round(experience_years or 0),
                    experience_years=experience_years,
                    summary=item.summary,
                    ai_explanation=ai_explanation,
                    explanation=explanation,
                )
            )

        return JobMatchResponse(
            job_id=job_id,
            total_candidates=len(candidates),
            matched_candidates=matches,
        )

    async def get_matches(self, job_id: str) -> JobMatchResponse:
        return await self.match_candidates(job_id)

    @staticmethod
    def get_match_recommendation(match_score: float) -> str:
        if match_score >= 90:
            return "Strong Match"
        if match_score >= 70:
            return "Good Match"
        if match_score >= 50:
            return "Moderate Match"
        return "Weak Match"
