from datetime import datetime, timedelta, timezone
from typing import Any

from neo4j import AsyncTransaction

from app.db.neo4j import Neo4jConnection

PROCESSING_TIMEOUT = timedelta(minutes=20)


class GmailMessageTrackingService:
    """Track Gmail attachment import attempts without storing message content."""

    def __init__(self, neo4j: Neo4jConnection) -> None:
        self.neo4j = neo4j

    async def claim_attachment(
        self,
        message_id: str,
        attachment_id: str,
        filename: str,
    ) -> dict[str, Any]:
        """Create an import record and atomically claim it for processing."""
        now = datetime.now(timezone.utc)

        async def claim(tx: AsyncTransaction) -> dict[str, Any]:
            result = await tx.run(
                """
                MERGE (a:GmailAttachment {
                    message_id: $message_id,
                    attachment_id: $attachment_id
                })
                ON CREATE SET
                    a.source = 'gmail',
                    a.status = 'PENDING',
                    a.imported_at = $now,
                    a.created_at = $now,
                    a.filename = $filename
                SET a.lock_version = coalesce(a.lock_version, 0) + 1
                RETURN properties(a) AS record
                """,
                {
                    "message_id": message_id,
                    "attachment_id": attachment_id,
                    "filename": filename,
                    "now": now.isoformat(),
                },
            )
            records = await result.data()
            record = records[0]["record"]
            status = record.get("status")

            if status is None:
                status = (
                    "SUCCESS"
                    if record.get("candidate_id")
                    else "FAILED"
                )
                await tx.run(
                    """
                    MATCH (a:GmailAttachment {
                        message_id: $message_id,
                        attachment_id: $attachment_id
                    })
                    SET a.status = $status,
                        a.source = 'gmail',
                        a.updated_at = $now
                    """,
                    {
                        "message_id": message_id,
                        "attachment_id": attachment_id,
                        "status": status,
                        "now": now.isoformat(),
                    },
                )
                record["status"] = status

            if status in {"SUCCESS", "DUPLICATE"}:
                return {"claimed": False, **record}

            if status == "PROCESSING" and not self._is_stale(
                record.get("updated_at"),
                now,
            ):
                return {"claimed": False, **record}

            await tx.run(
                """
                MATCH (a:GmailAttachment {
                    message_id: $message_id,
                    attachment_id: $attachment_id
                })
                SET a.status = 'PROCESSING',
                    a.source = 'gmail',
                    a.filename = $filename,
                    a.attempted_at = $now,
                    a.updated_at = $now,
                    a.failure_reason = null
                RETURN properties(a) AS record
                """,
                {
                    "message_id": message_id,
                    "attachment_id": attachment_id,
                    "filename": filename,
                    "now": now.isoformat(),
                },
            )
            return {
                "claimed": True,
                **record,
                "status": "PROCESSING",
                "imported_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "filename": filename,
            }

        return await self.neo4j.execute_write_transaction(claim)

    async def claim_hash(
        self,
        message_id: str,
        attachment_id: str,
        sha256: str,
    ) -> dict[str, Any]:
        """Reserve a content hash or report its successful prior import."""
        now = datetime.now(timezone.utc)

        async def claim(tx: AsyncTransaction) -> dict[str, Any]:
            result = await tx.run(
                """
                MERGE (h:GmailAttachmentHash {sha256: $sha256})
                ON CREATE SET
                    h.status = 'PENDING',
                    h.created_at = $now
                SET h.lock_version = coalesce(h.lock_version, 0) + 1
                RETURN properties(h) AS record
                """,
                {"sha256": sha256, "now": now.isoformat()},
            )
            records = await result.data()
            record = records[0]["record"]
            status = record.get("status")

            if status == "SUCCESS":
                return {
                    "claimed": False,
                    "duplicate": True,
                    "candidate_id": record.get("candidate_id"),
                }

            is_same_owner = (
                record.get("message_id") == message_id
                and record.get("attachment_id") == attachment_id
            )
            if status == "PROCESSING" and not is_same_owner and not self._is_stale(
                record.get("updated_at"),
                now,
            ):
                return {"claimed": False, "duplicate": False, "busy": True}

            await tx.run(
                """
                MATCH (h:GmailAttachmentHash {sha256: $sha256})
                SET h.status = 'PROCESSING',
                    h.message_id = $message_id,
                    h.attachment_id = $attachment_id,
                    h.updated_at = $now,
                    h.failure_reason = null
                """,
                {
                    "sha256": sha256,
                    "message_id": message_id,
                    "attachment_id": attachment_id,
                    "now": now.isoformat(),
                },
            )
            return {"claimed": True, "duplicate": False, "busy": False}

        return await self.neo4j.execute_write_transaction(claim)

    async def set_attachment_hash(
        self,
        message_id: str,
        attachment_id: str,
        sha256: str,
    ) -> None:
        await self.neo4j.execute_write(
            """
            MATCH (a:GmailAttachment {
                message_id: $message_id,
                attachment_id: $attachment_id
            })
            SET a.sha256 = $sha256,
                a.updated_at = $now
            """,
            {
                "message_id": message_id,
                "attachment_id": attachment_id,
                "sha256": sha256,
                "now": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def mark_duplicate(
        self,
        message_id: str,
        attachment_id: str,
        sha256: str,
        candidate_id: str | None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.neo4j.execute_write(
            """
            MATCH (a:GmailAttachment {
                message_id: $message_id,
                attachment_id: $attachment_id
            })
            SET a.status = 'DUPLICATE',
                a.sha256 = $sha256,
                a.candidate_id = $candidate_id,
                a.failure_reason = null,
                a.updated_at = $now
            """,
            {
                "message_id": message_id,
                "attachment_id": attachment_id,
                "sha256": sha256,
                "candidate_id": candidate_id,
                "now": now,
            },
        )

    async def mark_pending(
        self,
        message_id: str,
        attachment_id: str,
        reason: str,
    ) -> None:
        await self.neo4j.execute_write(
            """
            MATCH (a:GmailAttachment {
                message_id: $message_id,
                attachment_id: $attachment_id
            })
            SET a.status = 'PENDING',
                a.failure_reason = $reason,
                a.updated_at = $now
            """,
            {
                "message_id": message_id,
                "attachment_id": attachment_id,
                "reason": reason,
                "now": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def mark_failed(
        self,
        message_id: str,
        attachment_id: str,
        reason: str,
        sha256: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()

        async def mark(tx: AsyncTransaction) -> None:
            await tx.run(
                """
                MATCH (a:GmailAttachment {
                    message_id: $message_id,
                    attachment_id: $attachment_id
                })
                SET a.status = 'FAILED',
                    a.failure_reason = $reason,
                    a.sha256 = coalesce($sha256, a.sha256),
                    a.updated_at = $now
                """,
                {
                    "message_id": message_id,
                    "attachment_id": attachment_id,
                    "reason": reason,
                    "sha256": sha256,
                    "now": now,
                },
            )
            if sha256:
                await tx.run(
                    """
                    MATCH (h:GmailAttachmentHash {sha256: $sha256})
                    WHERE h.message_id = $message_id
                      AND h.attachment_id = $attachment_id
                    SET h.status = 'FAILED',
                        h.failure_reason = $reason,
                        h.updated_at = $now
                    """,
                    {
                        "sha256": sha256,
                        "message_id": message_id,
                        "attachment_id": attachment_id,
                        "reason": reason,
                        "now": now,
                    },
                )

        await self.neo4j.execute_write_transaction(mark)

    async def list_import_history(self, limit: int = 100) -> list[dict[str, Any]]:
        records = await self.neo4j.execute_read(
            """
            MATCH (a:GmailAttachment)
            OPTIONAL MATCH (c:Candidate {id: a.candidate_id})
            RETURN properties(a) AS import,
                   c.id AS candidate_id,
                   c.full_name AS candidate_name
            ORDER BY a.imported_at DESC
            LIMIT $limit
            """,
            {"limit": limit},
        )
        return records

    async def get_attachment_import(
        self,
        message_id: str,
        attachment_id: str,
    ) -> dict[str, Any] | None:
        records = await self.neo4j.execute_read(
            """
            MATCH (a:GmailAttachment {
                message_id: $message_id,
                attachment_id: $attachment_id
            })
            RETURN properties(a) AS record
            """,
            {"message_id": message_id, "attachment_id": attachment_id},
        )
        return records[0]["record"] if records else None

    async def is_attachment_processed(
        self,
        message_id: str,
        attachment_id: str,
    ) -> bool:
        """Compatibility helper used by existing callers."""
        result = await self.neo4j.execute_read(
            """
            OPTIONAL MATCH (a:GmailAttachment {
                message_id: $message_id,
                attachment_id: $attachment_id
            })
            RETURN a.status AS status,
                   a.candidate_id AS candidate_id
            """,
            {"message_id": message_id, "attachment_id": attachment_id},
        )
        if not result:
            return False
        return result[0].get("status") in {"SUCCESS", "DUPLICATE"} or bool(
            result[0].get("candidate_id")
        )

    @staticmethod
    def _is_stale(value: Any, now: datetime) -> bool:
        if not isinstance(value, str):
            return True
        try:
            updated = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return True
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        return now - updated > PROCESSING_TIMEOUT
