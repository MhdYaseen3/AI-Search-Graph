"""Manually reset development resume and candidate data.

Run from the backend directory with:
    python scripts/reset_development_data.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.neo4j import Neo4jConnection
from app.services.development_reset import reset_development_resume_data


async def main() -> None:
    connection = Neo4jConnection()
    await connection.connect()
    try:
        result = await reset_development_resume_data(connection)
        print(result)
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(main())