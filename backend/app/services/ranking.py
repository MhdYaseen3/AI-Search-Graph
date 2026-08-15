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
                    projects=candidate.get(
    "projects",
    [],
),
                    summary=candidate.get(
                        "summary",
                    ),
                )
            )

        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[: query.limit]

    def _compute_score(
        self,
        candidate: dict[str, Any],
        query: SearchQuery,
    ) -> float:
        """Compute weighted relevance score."""

        matched_skills = len(
            candidate.get("matched_skills", [])
        )

        matched_technologies = len(
            candidate.get("matched_technologies", [])
        )

        matched_projects = len(
            candidate.get("matched_projects", [])
        )

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

        query_score = self._query_relevance_score(
            candidate,
            query,
        )

        score = (
            skill_score * 0.40
            + technology_score * 0.25
            + project_score * 0.20
            + query_score * 0.15
        )

        return round(
            min(score, 1.0),
            2,
        )
    def _match_items(
        self,
        candidate_items: list[str],
        query_items: list[str],
    ) -> list[str]:
        """Match query items against candidate items."""
        candidate_normalized = {
            normalize_entity(item)
            for item in candidate_items
        }

        matched = []

        for item in query_items:
            normalized_query = normalize_entity(item)

            if normalized_query in candidate_normalized:
                matched.append(item)

        return matched

    def _query_relevance_score(
        self,
        candidate: dict[str, Any],
        query: SearchQuery,
    ) -> float:
        """Calculate relevance between the natural-language query and candidate data."""

        query_words = set(
            normalize_entity(word)
            for word in query.query.lower().split()
            if len(word) > 2
        )

        if not query_words:
            return 0.0

        candidate_text_parts = []

        candidate_text_parts.extend(
            candidate.get("skills", [])
        )

        candidate_text_parts.extend(
            candidate.get("technologies", [])
        )

        candidate_text_parts.extend(
            candidate.get("projects", [])
        )

        if candidate.get("summary"):
            candidate_text_parts.append(
                candidate["summary"]
            )

        candidate_text = " ".join(
            normalize_entity(str(item))
            for item in candidate_text_parts
        )

        candidate_words = set(
            word
            for word in candidate_text.split()
            if len(word) > 2
        )

        if not candidate_words:
            return 0.0

        matched_words = query_words.intersection(
            candidate_words
        )

        return len(matched_words) / len(query_words)
