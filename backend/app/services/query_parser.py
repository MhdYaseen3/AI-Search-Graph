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

    def parse(self, text: str, limit: int = 20) -> SearchQuery:
        text_lower = text.lower()
    
        skills = self._find_matches(
            text_lower,
            self.SKILLS,
        )
    
        technologies = self._find_matches(
            text_lower,
            self.TECHNOLOGIES,
        )
    
        projects = self._find_projects(text_lower)
    
        return SearchQuery(
            query=text,
            skills=normalize_entities(skills),
            technologies=normalize_entities(technologies),
            projects=normalize_entities(projects),
            limit=limit,
        )

    @staticmethod
    def _find_matches(
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