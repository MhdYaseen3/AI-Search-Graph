import json
from pathlib import Path
from typing import Optional


TOKEN_FILE = Path("data/gmail_token.json")


def save_token(token_data: dict) -> None:
    """Save Gmail OAuth token data locally."""

    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)

    with TOKEN_FILE.open("w", encoding="utf-8") as file:
        json.dump(token_data, file, indent=4)


def load_token() -> Optional[dict]:
    """Load Gmail OAuth token data."""

    if not TOKEN_FILE.exists():
        return None

    with TOKEN_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def delete_token() -> None:
    """Delete stored Gmail OAuth token."""

    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()