from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client(monkeypatch: pytest.MonkeyPatch) -> AsyncClient:
    mock_connection = AsyncMock()
    mock_connection.connect = AsyncMock()
    mock_connection.close = AsyncMock()
    monkeypatch.setattr("app.main.get_neo4j_connection", lambda: mock_connection)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
