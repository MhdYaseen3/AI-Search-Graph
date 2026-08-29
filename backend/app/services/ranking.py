import logging
from typing import Any

from app.core.config import settings
from app.schemas.search import RankedCandidate, SearchQuery
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

            ranked.append(
                RankedCandidate(
                    candidate_id=candidate.get("candidate_id", ""),
                    full_name=candidate.get("full_name", ""),
                    score=score,
                    experience_years=candidate.get("experience_years"),
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
                    summary=candidate.get("summary"),
                )
            )

        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[: query.limit]

    def _compute_score(
        self,
        candidate: dict[str, Any],
        query: SearchQuery,
    ) -> float:
        """Compute weighted relevance score with dynamic weights."""
        matched_skills = len(candidate.get("matched_skills", []))
        matched_technologies = len(
            candidate.get("matched_technologies", []),
        )
        matched_projects = len(candidate.get("matched_projects", []))

        requested_skills = len(query.skills)
        requested_technologies = len(query.technologies)
        requested_projects = len(query.projects)

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
            "skills": 0.40 if requested_skills else 0.0,
            "technologies": 0.25 if requested_technologies else 0.0,
            "projects": 0.20 if requested_projects else 0.0,
            "experience": 0.25 if query.min_experience_years else 0.0,
            "query": 0.15,
        }

        weight_total = sum(weights.values())
        if weight_total == 0:
            weights["query"] = 1.0
            weight_total = 1.0

        score = (
            skill_score * weights["skills"] / weight_total
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
