import logging
from typing import Any

from app.core.config import settings
from app.schemas.search import MatchBreakdown, RankedCandidate, SearchQuery
from app.utils.entity_normalizer import normalize_entity

logger = logging.getLogger(__name__)


class RankingService:
    """Ranks search results by relevance score."""

    def rank(
        self,
        candidates: list[dict[str, Any]],
        query: SearchQuery,
    ) -> list[RankedCandidate]:
        """Score and sort candidates by match quality."""
        ranked: list[RankedCandidate] = []

        for candidate in candidates:
            score = self._compute_score(candidate, query)
            if score < settings.min_rank_score:
                continue

            match_breakdown = self._compute_match_breakdown(candidate, query)
            explanation = self._build_match_explanation(candidate, query)

            ranked.append(
                RankedCandidate(
                    candidate_id=candidate.get("candidate_id", ""),
                    full_name=candidate.get("full_name", ""),
                    score=score,
                    experience_years=candidate.get("experience_years"),
                    matched_roles=candidate.get(
                        "matched_roles",
                        [],
                    ),
                    matched_skills=candidate.get(
                        "matched_skills",
                        [],
                    ),
                    matched_technologies=candidate.get(
                        "matched_technologies",
                        [],
                    ),
                    matched_projects=candidate.get(
                        "matched_projects",
                        [],
                    ),
                    match_breakdown=match_breakdown,
                    explanation=explanation,
                    summary=candidate.get("summary"),
                )
            )

        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[: query.limit]

    def _build_match_explanation(
        self,
        candidate: dict[str, Any],
        query: SearchQuery,
    ) -> str:
        """Build deterministic match explanation using available data."""
        parts: list[str] = []

        # Role match
        if query.role:
            matched_roles = candidate.get("matched_roles", [])
            if matched_roles:
                parts.append(f"Role: Match ({matched_roles[0]})")
            else:
                parts.append("Role: No match")

        # Experience match
        if query.min_experience_years is not None:
            experience_years = candidate.get("experience_years") or 0.0
            if experience_years >= query.min_experience_years:
                parts.append(
                    f"Experience: Match ({experience_years} years, "
                    f"requested {query.min_experience_years}+ years)"
                )
            else:
                parts.append(
                    f"Experience: No match ({experience_years} years, "
                    f"requested {query.min_experience_years}+ years)"
                )

        # Skills match
        if query.skills:
            matched_skills = candidate.get("matched_skills", [])
            if matched_skills:
                parts.append(f"Skills matched: {', '.join(matched_skills)}")
            else:
                parts.append("Skills: No match")

        # Technologies match
        if query.technologies:
            matched_technologies = candidate.get("matched_technologies", [])
            if matched_technologies:
                parts.append(f"Technologies matched: {', '.join(matched_technologies)}")
            else:
                parts.append("Technologies: No match")

        # Projects match
        if query.projects:
            matched_projects = candidate.get("matched_projects", [])
            if matched_projects:
                parts.append(f"Projects matched: {', '.join(matched_projects)}")
            else:
                parts.append("Projects: No match")

        return ". ".join(parts) if parts else "Match based on profile overlap."

    def _compute_match_breakdown(
        self,
        candidate: dict[str, Any],
        query: SearchQuery,
    ) -> MatchBreakdown:
        """Compute structured breakdown of match components."""
        role_match = bool(
            query.role and len(candidate.get("matched_roles", [])) > 0
        )

        experience_match = True
        if query.min_experience_years is not None:
            experience_years = candidate.get("experience_years") or 0.0
            experience_match = experience_years >= query.min_experience_years

        skill_match = bool(
            len(query.skills) > 0
            and len(candidate.get("matched_skills", [])) > 0
        )

        technology_match = bool(
            len(query.technologies) > 0
            and len(candidate.get("matched_technologies", [])) > 0
        )

        project_match = bool(
            len(query.projects) > 0
            and len(candidate.get("matched_projects", [])) > 0
        )

        return MatchBreakdown(
            role_match=role_match,
            experience_match=experience_match,
            skill_match=skill_match,
            technology_match=technology_match,
            project_match=project_match,
        )

    def _compute_score(
        self,
        candidate: dict[str, Any],
        query: SearchQuery,
    ) -> float:
        """Compute weighted relevance score with dynamic weights."""
        matched_roles = len(candidate.get("matched_roles", []))
        matched_skills = len(candidate.get("matched_skills", []))
        matched_technologies = len(
            candidate.get("matched_technologies", []),
        )
        matched_projects = len(candidate.get("matched_projects", []))

        requested_roles = 1 if query.role else 0
        requested_skills = len(query.skills)
        requested_technologies = len(query.technologies)
        requested_projects = len(query.projects)

        role_score = 1.0 if matched_roles > 0 and query.role else 0.0

        skill_score = (
            matched_skills / requested_skills
            if requested_skills
            else 0.0
        )

        technology_score = (
            matched_technologies / requested_technologies
            if requested_technologies
            else 0.0
        )

        project_score = (
            matched_projects / requested_projects
            if requested_projects
            else 0.0
        )

        experience_score = self._experience_score(candidate, query)
        query_score = self._query_relevance_score(candidate, query)

        weights = {
            "role": 0.20 if query.role else 0.0,
            "skills": 0.35 if requested_skills else 0.0,
            "technologies": 0.20 if requested_technologies else 0.0,
            "projects": 0.15 if requested_projects else 0.0,
            "experience": 0.20 if query.min_experience_years else 0.0,
            "query": 0.10,
        }

        weight_total = sum(weights.values())
        if weight_total == 0:
            weights["query"] = 1.0
            weight_total = 1.0

        score = (
            role_score * weights["role"] / weight_total
            + skill_score * weights["skills"] / weight_total
            + technology_score * weights["technologies"] / weight_total
            + project_score * weights["projects"] / weight_total
            + experience_score * weights["experience"] / weight_total
            + query_score * weights["query"] / weight_total
        )

        return round(min(score, 1.0), 2)

    def _experience_score(
         self,
         candidate: dict[str, Any],
         query: SearchQuery,
     ) -> float:
         """Score experience relative to the requested minimum."""
         if query.min_experience_years is None:
             return 0.0

         experience_years = candidate.get("experience_years") or 0.0
         minimum_years = query.min_experience_years

         if experience_years < minimum_years:
             return 0.0

         # Reward experience above the requested minimum,
         # while keeping the score bounded.
         excess_ratio = (
             experience_years - minimum_years
         ) / max(minimum_years, 1.0)

         return min(
             1.0,
             0.5 + (0.5 * excess_ratio),
         )

    def _query_relevance_score(
        self,
        candidate: dict[str, Any],
        query: SearchQuery,
    ) -> float:
        """Calculate relevance between the natural-language query and candidate data."""
        query_words = {
            normalize_entity(word)
            for word in query.query.lower().split()
            if len(word) > 2
        }

        if not query_words:
            return 0.0

        candidate_text_parts: list[str] = []
        candidate_text_parts.extend(candidate.get("skills", []))
        candidate_text_parts.extend(candidate.get("technologies", []))
        candidate_text_parts.extend(candidate.get("projects", []))
        candidate_text_parts.extend(candidate.get("roles", []))

        if candidate.get("summary"):
            candidate_text_parts.append(candidate["summary"])

        for experience in candidate.get("experiences", []):
            if experience.get("role"):
                candidate_text_parts.append(experience["role"])
            if experience.get("company"):
                candidate_text_parts.append(experience["company"])

        candidate_text = " ".join(
            normalize_entity(str(item))
            for item in candidate_text_parts
        )

        candidate_words = {
            word
            for word in candidate_text.split()
            if len(word) > 2
        }

        if not candidate_words:
            return 0.0

        matched_words = query_words.intersection(candidate_words)
        return len(matched_words) / len(query_words)
