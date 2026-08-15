import re


ALIASES = {
    "react.js": "react",
    "reactjs": "react",
    "nodejs": "node.js",
    "express": "express.js",
    "expressjs": "express.js",
    "postgres": "postgresql",
    "mongo": "mongodb",
    "mysql": "mysql",
    "py": "python",
}


def normalize_entity(value: str) -> str:
    """Normalize extracted/search entities for consistent matching."""

    value = value.strip().lower()

    # Remove bullets, dashes, stars and other list prefixes.
    value = re.sub(r"^[•●▪◦*-]+\s*", "", value)

    # Normalize repeated whitespace.
    value = re.sub(r"\s+", " ", value).strip()

    # Apply known aliases.
    return ALIASES.get(value, value)


def normalize_entities(values: list[str]) -> list[str]:
    """Normalize and deduplicate a list of entities."""

    normalized = []

    for value in values:
        value = normalize_entity(value)

        if value and value not in normalized:
            normalized.append(value)

    return normalized