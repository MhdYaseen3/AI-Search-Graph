import re

from app.schemas.search import SearchQuery
from app.utils.entity_normalizer import normalize_entities


class QueryParser:
    """Convert natural-language search queries into structured search filters."""

    SKILLS = {
        "python",
        "java",
        "javascript",
        "sql",
        "c++",
        "c#",
        "fastapi",
        "django",
        "flask",
        "react",
    }

    TECHNOLOGIES = {
        "node.js",
        "nodejs",
        "express.js",
        "express",
        "mongodb",
        "postgresql",
        "mysql",
        "neo4j",
        "docker",
        "tensorflow",
        "pytorch",
        "git",
        "github",
    }

    PROJECT_KEYWORDS = {
        "ai graph search engine",
        "task management",
        "smart housing",
    }

    ROLES = {
        "backend developer": ["backend developer", "backend engineer"],
        "frontend developer": ["frontend developer", "frontend engineer"],
        "full stack developer": ["full stack developer", "full stack engineer"],
        "software developer": ["software developer", "software engineer"],
        "data scientist": ["data scientist"],
        "devops engineer": ["devops engineer", "devops"],
    }

    def parse(self, text: str, limit: int = 20) -> SearchQuery:
        text_lower = text.lower()

        role = self._find_roles(text_lower)

        skills = self._find_matches(
            text_lower,
            self.SKILLS,
        )

        technologies = self._find_matches(
            text_lower,
            self.TECHNOLOGIES,
        )

        projects = self._find_projects(text_lower)

        min_experience_years = self._find_min_experience_years(
            text_lower
        )

        return SearchQuery(
            query=text,
            role=role,
            skills=normalize_entities(skills),
            technologies=normalize_entities(technologies),
            projects=normalize_entities(projects),
            min_experience_years=min_experience_years,
            limit=limit,
        )
    def _find_matches(
        self,
        text: str,
        items: set[str],
    ) -> list[str]:
        matches = []

        for item in items:
            pattern = rf"(?<!\w){re.escape(item)}(?!\w)"

            if re.search(pattern, text):
                matches.append(item)

        return matches

    def _find_projects(self, text: str) -> list[str]:
        """Find known project names mentioned in the query."""

        matches = []

        for project in self.PROJECT_KEYWORDS:
            if project in text:
                matches.append(project)

        return matches

    def _find_min_experience_years(self, text: str) -> float | None:
        """Extract minimum years of experience from a natural-language query."""
        patterns = [
            r"\b(\d+(?:\.\d+)?)\s*\+\s*years?\b",
            r"\bat\s+least\s+(\d+(?:\.\d+)?)\s+years?\b",
            r"\bminimum\s+(\d+(?:\.\d+)?)\s+years?\b",
            r"\b(\d+(?:\.\d+)?)\s+years?\s+of\s+experience\b",
            r"\b(\d+(?:\.\d+)?)\s+years?\s+experience\b",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)

            if match:
                return float(match.group(1))

        return None

    def _find_roles(self, text: str) -> str | None:
        """Find job role mentions in the query and return canonical role name."""
        for canonical_role, aliases in self.ROLES.items():
            for alias in aliases:
                # Handle both singular and plural forms
                alias_variants = [alias]
                if alias.endswith("er"):
                    alias_variants.append(alias + "s")
                elif alias.endswith("engineer"):
                    alias_variants.append(alias.replace("engineer", "engineers"))
                elif alias.endswith("developer"):
                    alias_variants.append(alias.replace("developer", "developers"))
                elif alias.endswith("scientist"):
                    alias_variants.append(alias.replace("scientist", "scientists"))

                for variant in alias_variants:
                    pattern = rf"(?<!\w){re.escape(variant)}(?!\w)"
                    if re.search(pattern, text, re.IGNORECASE):
                        return canonical_role

        return None