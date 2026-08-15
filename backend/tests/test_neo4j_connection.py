from unittest.mock import AsyncMock

import pytest

from app.db.neo4j import Neo4jConnection


@pytest.mark.asyncio
async def test_neo4j_connection_lifecycle() -> None:
    connection = Neo4jConnection()

    assert connection.is_connected is False

    mock_driver = AsyncMock()
    mock_driver.verify_connectivity = AsyncMock()
    mock_driver.close = AsyncMock()

    connection._driver = mock_driver
    connection._connected = True

    assert connection.is_connected is True

    await connection.close()

    mock_driver.close.assert_awaited_once()
    assert connection.is_connected is False


@pytest.mark.asyncio
async def test_neo4j_health_check_disconnected() -> None:
    connection = Neo4jConnection()
    status = await connection.health_check()

    assert status["status"] == "disconnected"
