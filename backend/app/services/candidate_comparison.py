"""Service for comparing multiple candidates using actual graph data."""

import logging
from typing import Any

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.db.neo4j import Neo4jConnection
from app.schemas.comparison import (
    CandidateComparisonData,
    ComparisonMetrics,
    ComparisonRequest,
    ComparisonResult,
)
from app.services.ai_summary import AISummaryService
from app.utils.experience_calc import calculate_experience_years

logger = logging.getLogger(__name__)


class CandidateComparisonService:
    """Service for comparing candidates using actual Neo4j data."""

    def __init__(
        self,
        neo4j: Neo4jConnection,
        ai_summary_service: AISummaryService | None = None,
    ) -> None:
        self.neo4j = neo4j
        self.ai_summary_service = ai_summary_service

    async def compare_candidates(
        self,
        request: ComparisonRequest,
    ) -> ComparisonResult:
        """Compare multiple candidates using actual graph data.

        Args:
            request: Comparison request with candidate IDs

        Returns:
            ComparisonResult with actual candidate data and metrics
        """
        # Fetch actual candidate data
        candidates_data = []
        for candidate_id in request.candidate_ids:
            try:
                candidate_data = await self._fetch_candidate_data(candidate_id)
                candidates_data.append(candidate_data)
            except NotFoundError as e:
                logger.error("Candidate not found: %s", candidate_id)
                return ComparisonResult(
                    candidates=[],
                    error=f"Candidate {candidate_id} not found",
                )

        if not candidates_data:
            return ComparisonResult(
                candidates=[],
                error="No valid candidates found for comparison",
            )

        # Calculate objective comparison metrics
        metrics = self._calculate_metrics(candidates_data)

        # Generate AI comparative analysis
        ai_analysis = None
        recommendation = None

        if self.ai_summary_service:
            try:
                ai_analysis, recommendation = await self._generate_ai_comparison(
                    candidates_data,
                    metrics,
                )
            except Exception as e:
                logger.warning("AI comparison failed: %s", e)
                ai_analysis = "AI comparative analysis unavailable"
                recommendation = None
        else:
            # Use fallback when AI service is not available
            ai_analysis = self._build_fallback_comparison(candidates_data, metrics)
            recommendation = self._build_fallback_recommendation(candidates_data)

        return ComparisonResult(
            candidates=candidates_data,
            metrics=metrics,
            ai_analysis=ai_analysis,
            recommendation=recommendation,
        )

    async def _fetch_candidate_data(
        self,
        candidate_id: str,
    ) -> CandidateComparisonData:
        """Fetch actual candidate data from Neo4j."""
        query = """
        MATCH (c:Candidate {id: $id})
        OPTIONAL MATCH (c)-[:HAS_SKILL]->(s:Skill)
        OPTIONAL MATCH (c)-[:WORKED_ON]->(p:Project)
        OPTIONAL MATCH (c)-[:USES_TECHNOLOGY]->(t:Technology)
        OPTIONAL MATCH (c)-[:STUDIED_AT]->(e:Education)
        OPTIONAL MATCH (c)-[:WORKED_AT]->(x:Experience)
        RETURN
            c.id AS candidate_id,
            c.full_name AS full_name,
            c.email AS email,
            c.summary AS summary,
            collect(DISTINCT s.name) AS skills,
            collect(DISTINCT p.name) AS projects,
            collect(DISTINCT t.name) AS technologies,
            collect(DISTINCT e.institution) AS education,
            collect(DISTINCT {
                company: x.company,
                role: x.role,
                start_date: x.start_date,
                end_date: x.end_date
            }) AS experiences
        """

        data = await self.neo4j.execute_read(query, {"id": candidate_id})
        if not data:
            raise NotFoundError(f"Candidate {candidate_id} not found")

        record = data[0]

        # Filter experiences to valid ones
        experiences = [
            exp
            for exp in record.get("experiences", [])
            if exp and exp.get("company")
        ]

        # Calculate experience years
        experience_years = calculate_experience_years(experiences)

        # If no valid experience data (0 years with no experiences), set to None
        if experience_years == 0.0 and not experiences:
            experience_years = None

        return CandidateComparisonData(
            candidate_id=record["candidate_id"],
            full_name=record["full_name"],
            email=record.get("email"),
            summary=record.get("summary"),
            skills=record.get("skills") or [],
            technologies=record.get("technologies") or [],
            projects=record.get("projects") or [],
            education=record.get("education") or [],
            experiences=experiences,
            experience_years=experience_years,
        )

    def _calculate_metrics(
        self,
        candidates: list[CandidateComparisonData],
    ) -> dict[str, ComparisonMetrics]:
        """Calculate objective comparison metrics between candidates."""
        metrics: dict[str, ComparisonMetrics] = {}

        for i, cand_a in enumerate(candidates):
            for j, cand_b in enumerate(candidates):
                if i >= j:
                    continue  # Only calculate each pair once

                key = f"{cand_a.candidate_id}_vs_{cand_b.candidate_id}"

                # Skill overlap: percentage of shared skills relative to total unique skills
                skills_a = set(s.lower() for s in cand_a.skills)
                skills_b = set(s.lower() for s in cand_b.skills)
                shared_skills = skills_a & skills_b
                all_skills = skills_a | skills_b

                skill_overlap = (
                    int(len(shared_skills) / len(all_skills) * 100) if all_skills else 0
                )

                # Skill coverage: percentage of candidate A's skills covered by candidate B's skills
                # and vice versa, averaged. This represents how well each candidate's skills
                # are represented in the other's skill set. Bounded by 100%.
                if skills_a and skills_b:
                    coverage_a_to_b = len(skills_a & skills_b) / len(skills_a) * 100
                    coverage_b_to_a = len(skills_b & skills_a) / len(skills_b) * 100
                    skill_coverage = int((coverage_a_to_b + coverage_b_to_a) / 2)
                else:
                    skill_coverage = 0

                # Technology overlap
                tech_a = set(t.lower() for t in cand_a.technologies)
                tech_b = set(t.lower() for t in cand_b.technologies)
                shared_tech = tech_a & tech_b
                all_tech = tech_a | tech_b

                technology_overlap = (
                    int(len(shared_tech) / len(all_tech) * 100) if all_tech else 0
                )

                # Experience difference
                total_experience_diff = None
                if cand_a.experience_years is not None and cand_b.experience_years is not None:
                    total_experience_diff = abs(
                        cand_a.experience_years - cand_b.experience_years
                    )

                # Project count difference
                project_count_diff = abs(len(cand_a.projects) - len(cand_b.projects))

                metrics[key] = ComparisonMetrics(
                    skill_overlap=skill_overlap,
                    skill_coverage=skill_coverage,
                    technology_overlap=technology_overlap,
                    total_experience_diff=total_experience_diff,
                    project_count_diff=project_count_diff,
                )

        return metrics

    async def _generate_ai_comparison(
        self,
        candidates: list[CandidateComparisonData],
        metrics: dict[str, ComparisonMetrics],
    ) -> tuple[str, str]:
        """Generate AI comparative analysis using actual candidate data."""

        # Build comparison prompt with actual data
        prompt = self._build_comparison_prompt(candidates, metrics)

        try:
            analysis = await self.ai_summary_service._call_ollama(prompt)
            recommendation = self._extract_recommendation(analysis, candidates)
            return analysis.strip(), recommendation
        except Exception as e:
            logger.warning("AI comparison generation failed: %s", e)
            return self._build_fallback_comparison(candidates, metrics), self._build_fallback_recommendation(candidates)

    def _build_comparison_prompt(
        self,
        candidates: list[CandidateComparisonData],
        metrics: dict[str, ComparisonMetrics],
    ) -> str:
        """Build AI prompt with actual candidate comparison data."""

        # Build ID to name mapping for metrics
        id_to_name = {cand.candidate_id: cand.full_name for cand in candidates}

        candidate_descriptions = []
        for cand in candidates:
            desc = f"""
{cand.full_name}:
Skills: {', '.join(cand.skills[:10])}
Technologies: {', '.join(cand.technologies[:8])}
Projects: {', '.join(cand.projects[:5])}
Experience: {cand.experience_years or 'Unknown'} years
Education: {', '.join(cand.education[:3])}
"""
            candidate_descriptions.append(desc)

        # Convert metric keys (with IDs) to readable names
        metrics_description = "\n".join(
            f"{id_to_name.get(key.split('_vs_')[0], key.split('_vs_')[0])} vs {id_to_name.get(key.split('_vs_')[1], key.split('_vs_')[1])}: "
            f"skill overlap={m.skill_overlap}%, skill coverage={m.skill_coverage}%, technology overlap={m.technology_overlap}%"
            for key, m in metrics.items()
        )

        prompt = f"""
You are a recruitment comparison system.

Compare the following candidates based on their actual data:

{''.join(candidate_descriptions)}

COMPARISON METRICS:
{metrics_description}

CRITICAL SAFETY RULES:
- Use ONLY the candidate data provided above.
- Do NOT invent skills, technologies, experience, projects, or qualifications.
- Do NOT use example candidate names or data.
- Compare the ACTUAL candidates listed above using their FULL NAMES.
- Never use generic numbered labels or placeholder names. Always use the actual names.
- Highlight strengths and gaps based on the provided data.
- Provide a hiring recommendation based on the comparison.
- If information is unavailable, state that it is unavailable.
- Output PLAIN TEXT without markdown formatting, asterisks, or special characters.
- Use normal paragraphs and clear sentences.

Write 4-5 sentences comparing these candidates by name, highlighting their relative strengths and differences.
Then provide a specific hiring recommendation based on the comparison.
"""

        return prompt

    def _extract_recommendation(
        self,
        analysis: str,
        candidates: list[CandidateComparisonData],
    ) -> str:
        """Extract recommendation from AI analysis."""
        # Simple extraction - look for recommendation-like sentences
        lower_analysis = analysis.lower()

        # Check for explicit recommendation keywords
        recommendation_keywords = ["recommend", "hire", "select", "choose", "prefer"]
        sentences = analysis.split(".")

        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in recommendation_keywords):
                # Clean up and return the recommendation
                recommendation = sentence.strip()
                if len(recommendation) > 200:
                    recommendation = recommendation[:200] + "..."
                return recommendation

        # Fallback: generate based on data
        return self._build_fallback_recommendation(candidates)

    def _build_fallback_comparison(
        self,
        candidates: list[CandidateComparisonData],
        metrics: dict[str, ComparisonMetrics],
    ) -> str:
        """Build fallback comparison using actual data."""
        if not candidates:
            return "No candidates available for comparison."

        # Build ID to name mapping
        id_to_name = {cand.candidate_id: cand.full_name for cand in candidates}

        parts = [f"Comparing {len(candidates)} candidates based on their actual profiles:"]

        for cand in candidates:
            parts.append(
                f"{cand.full_name}: "
                f"{len(cand.skills)} skills, "
                f"{len(cand.technologies)} technologies, "
                f"{len(cand.projects)} projects, "
                f"{cand.experience_years or 'unknown'} years experience."
            )

        if metrics:
            metric_parts = []
            for key, metric in metrics.items():
                if "_vs_" in key:
                    id_a, id_b = key.split("_vs_")
                    name_a = id_to_name.get(id_a, id_a)
                    name_b = id_to_name.get(id_b, id_b)
                    metric_parts.append(
                        f"Skill overlap between {name_a} and {name_b} is {metric.skill_overlap}% with {metric.skill_coverage}% coverage."
                    )
            if metric_parts:
                parts.append(" ".join(metric_parts))

        return " ".join(parts)

    def _build_fallback_recommendation(
        self,
        candidates: list[CandidateComparisonData],
    ) -> str:
        """Build fallback recommendation based on actual data."""
        if not candidates:
            return "Unable to provide recommendation - no candidates available."

        # Simple heuristic based on experience and skills
        try:
            best_candidate = max(
                candidates,
                key=lambda c: (c.experience_years or 0, len(c.skills)),
            )
        except (ValueError, TypeError):
            # Handle empty or invalid candidates
            if candidates:
                best_candidate = candidates[0]
            else:
                return "Unable to provide recommendation - no valid candidates available."

        second_best = None
        if len(candidates) > 1:
            try:
                second_best = max(
                    (c for c in candidates if c != best_candidate),
                    key=lambda c: (c.experience_years or 0, len(c.skills)),
                )
            except (ValueError, TypeError):
                second_best = None

        if second_best:
            return (
                f"{best_candidate.full_name} has the strongest combination of experience "
                f"({best_candidate.experience_years or 'unknown'} years) and skills "
                f"({len(best_candidate.skills)}). {second_best.full_name} shows complementary strengths. "
                f"Consider role requirements when making final decision."
            )
        else:
            return (
                f"{best_candidate.full_name} demonstrates strong credentials with "
                f"{len(best_candidate.skills)} skills and {best_candidate.experience_years or 'unknown'} years experience."
            )
