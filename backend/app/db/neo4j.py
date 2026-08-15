import logging
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any, TypeVar

from neo4j import AsyncDriver, AsyncGraphDatabase, AsyncSession, AsyncTransaction

from app.core.config import settings
from app.core.exceptions import DatabaseError
from app.db.nodes.constraints import SCHEMA_STATEMENTS

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Neo4jConnection:
    """Manages the Neo4j async driver lifecycle, schema, and session access."""

    def __init__(self) -> None:
        self._driver: AsyncDriver | None = None
        self._connected: bool = False

    @property
    def is_connected(self) -> bool:
        return self._driver is not None and self._connected

    async def connect(self) -> None:
        if self.is_connected:
            return

        try:
            self._driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
                max_connection_pool_size=settings.neo4j_max_connection_pool_size,
                connection_timeout=settings.neo4j_connection_timeout,
            )
            await self._driver.verify_connectivity()
            self._connected = True
            logger.info("Neo4j connection established")

            if settings.neo4j_schema_init:
                await self.initialize_schema()
        except DatabaseError:
            raise
        except Exception as exc:
            self._driver = None
            self._connected = False
            logger.exception("Failed to connect to Neo4j")
            raise DatabaseError("Unable to connect to Neo4j") from exc

    async def close(self) -> None:
        if self._driver is not None:
            await self._driver.close()
            self._driver = None
            self._connected = False
            logger.info("Neo4j connection closed")

    async def health_check(self) -> dict[str, Any]:
        """Verify database connectivity and return status metadata."""
        if not self.is_connected:
            return {"status": "disconnected", "database": settings.neo4j_database}

        try:
            records = await self.execute_read(
                "RETURN 1 AS ok, db.name() AS database",
            )
            record = records[0] if records else {}
            return {
                "status": "connected",
                "database": record.get("database", settings.neo4j_database),
                "ok": record.get("ok") == 1,
            }
        except Exception as exc:
            logger.exception("Neo4j health check failed")
            return {
                "status": "unhealthy",
                "database": settings.neo4j_database,
                "error": str(exc),
            }

    async def initialize_schema(self) -> None:
        """Apply uniqueness constraints and indexes for graph node models."""
        for statement in SCHEMA_STATEMENTS:
            try:
                await self.execute_write(statement)
            except Exception as exc:
                logger.exception("Failed to apply schema statement: %s", statement)
                raise DatabaseError("Failed to initialize Neo4j schema") from exc

        logger.info("Neo4j schema initialized")

    @property
    def driver(self) -> AsyncDriver:
        if self._driver is None or not self._connected:
            raise DatabaseError("Neo4j driver is not initialized")
        return self._driver

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.driver.session(database=settings.neo4j_database) as session:
            yield session

    async def _run_in_transaction(
        self,
        work: Callable[[AsyncTransaction], Awaitable[T]],
        *,
        write: bool,
    ) -> T:
        async with self.session() as session:
            try:
                if write:
                    return await session.execute_write(work)
                return await session.execute_read(work)
            except DatabaseError:
                raise
            except Exception as exc:
                operation = "write" if write else "read"
                logger.exception("Neo4j %s transaction failed", operation)
                raise DatabaseError(f"Neo4j {operation} operation failed") from exc

    async def execute_read(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        params = parameters or {}

        async def _work(tx: AsyncTransaction) -> list[dict[str, Any]]:
            result = await tx.run(query, params)
            return await result.data()

        return await self._run_in_transaction(_work, write=False)

    async def execute_write(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        params = parameters or {}

        async def _work(tx: AsyncTransaction) -> list[dict[str, Any]]:
            result = await tx.run(query, params)
            return await result.data()

        return await self._run_in_transaction(_work, write=True)


_neo4j_connection = Neo4jConnection()


def get_neo4j_connection() -> Neo4jConnection:
    return _neo4j_connection
