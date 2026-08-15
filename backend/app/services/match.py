import logging

from app.core.exceptions import NotFoundError
from app.db.neo4j import Neo4jConnection
from app.models.candidate import Candidate
from app.models.job import Job
from app.schemas.match import JobMatchResponse, MatchedCandidate
from app.db.nodes.candidate import CandidateNode
from app.services.ai_match_explanation import AIMatchExplanationService
# from backend.app.api.v1.endpoints import candidates

logger = logging.getLogger(__name__)


class MatchService:
    """Service responsible for matching candidates with jobs."""

    def __init__(self, neo4j: Neo4jConnection, ai_explanation_service: AIMatchExplanationService,) -> None:
        self.neo4j = neo4j
        self.ai_explanation_service = ai_explanation_service

    async def match_candidates(self, job_id: str) -> JobMatchResponse:
        """
        Match all candidates against the given job and
        return them sorted by match score.
        """
        from app.db.nodes import JobNode, CandidateNode
        
        # Fetch the job by ID
        job_query = """
        MATCH (j:Job {id: $job_id})
        RETURN j
        """
        job_records = await self.neo4j.execute_read(job_query, {"job_id": job_id})
        if not job_records:
            raise NotFoundError(f"Job {job_id} not found")
        
        job = JobNode.from_neo4j(job_records[0]["j"]).to_domain()
        
        # Fetch all candidates
        candidates_query = """
         MATCH (c:Candidate)
         
         OPTIONAL MATCH (c)-[:HAS_SKILL]->(s:Skill)
         OPTIONAL MATCH (c)-[:USES_TECHNOLOGY]->(t:Technology)
         
         RETURN
             c,
             collect(DISTINCT s.name) AS skills,
             collect(DISTINCT t.name) AS technologies
         """
        
        candidate_records = await self.neo4j.execute_read(candidates_query)
        
        candidates = []
        
        for record in candidate_records:
         candidate = CandidateNode.from_neo4j(
             record["c"]
         ).to_domain()
     
         candidate.skills = record["skills"] or []
     
         candidates.append(candidate)
        
        # Calculate match score for each candidate and sort by score descending
        matched_candidates = []
        for candidate in candidates:
            matched = self.calculate_match_score(job, candidate)
            try:
                recommendation = self.get_match_recommendation(
                matched.match_score
            )
            
                matched.ai_explanation = await self.ai_explanation_service.generate_explanation(
                job_title=job.title,
                matched_skills=matched.matched_skills,
                missing_skills=matched.missing_skills,
                match_score=matched.match_score,
                recommendation=recommendation,
            )
                print("AI Explanation:", matched.ai_explanation)
            except Exception:
                logger.exception("Failed to generate AI match explanation")
                matched.ai_explanation = "Unable to generate AI explanation at this time."

            matched_candidates.append(matched)

        matched_candidates.sort(key=lambda m: m.match_score, reverse=True)
        
        return JobMatchResponse(
            job_id=job_id,
            total_candidates=len(candidates),
            matched_candidates=matched_candidates,
        )

    def calculate_match_score(
        self,
        job: Job,
        candidate: Candidate,
    ) -> MatchedCandidate:
        """
        Calculate the match score for one candidate.
        """
        # Normalize skills to lowercase for case-insensitive comparison
        required_skills_lower = {skill.lower() for skill in job.required_skills}
        print("Job Skills:", job.required_skills)
        print("Candidate Skills:", candidate.skills)
        candidate_skills_lower = {skill.lower() for skill in candidate.skills}
        
        # Find matched and missing skills
        matched_skills = required_skills_lower & candidate_skills_lower
        missing_skills = required_skills_lower - candidate_skills_lower
        
        # Calculate match score
        total_required = len(job.required_skills)
        match_score = (len(matched_skills) / total_required * 100) if total_required > 0 else 0.0
        
        # Return matched candidate with original case preserved
        matched_skills_list = [
            skill for skill in candidate.skills 
            if skill.lower() in matched_skills
        ]
        missing_skills_list = list(missing_skills)
        
        return MatchedCandidate(
            candidate_id=candidate.id,
            full_name=candidate.full_name,
            match_score=match_score,
            matched_skills=matched_skills_list,
            missing_skills=missing_skills_list,
            experience=job.experience,
            summary=candidate.summary,
        )

    async def get_matches(self, job_id: str) -> JobMatchResponse:
        """
        Return previously generated matches for a job.
        """
        raise NotImplementedError

    def get_match_recommendation(self, match_score: float) -> str:
     if match_score >= 90:
        return "Strong Match"
     elif match_score >= 70:
         return "Good Match"
     elif match_score >= 50:
         return "Moderate Match"
     else:
         return "Weak Match"