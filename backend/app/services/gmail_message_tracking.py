from datetime import datetime

from app.db.neo4j import Neo4jConnection


class GmailMessageTrackingService:
    """Track Gmail messages that have already been processed."""

    def __init__(self, neo4j: Neo4jConnection) -> None:
        self.neo4j = neo4j

    async def is_processed(self, message_id: str) -> bool:
        """Return True if the Gmail message was already processed."""

        query = """
        MATCH (m:GmailMessage {message_id: $message_id})
        RETURN count(m) AS count
        """

        records = await self.neo4j.execute_read(
            query,
            {"message_id": message_id},
        )

        return bool(
            records
            and records[0]["count"] > 0
        )

    async def mark_processed(
        self,
        message_id: str,
        candidate_id: str,
    ) -> None:
        """Mark a Gmail message as successfully processed."""

        query = """
        MERGE (m:GmailMessage {message_id: $message_id})
        SET
            m.processed_at = $processed_at,
            m.candidate_id = $candidate_id
        """

        await self.neo4j.execute_write(
            query,
            {
                "message_id": message_id,
                "processed_at": datetime.utcnow().isoformat(),
                "candidate_id": candidate_id,
            },
        )