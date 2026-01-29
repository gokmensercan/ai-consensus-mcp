"""SQLite-backed per-agent inbox for inter-agent messaging"""

import json

from config import settings
from models.orchestration import InboxSummary, Message

from .database import get_db, init_db


class AgentInbox:
    """Manages per-agent message inboxes in SQLite."""

    @property
    def max_messages_per_agent(self) -> int:
        return settings.INBOX_MAX_MESSAGES

    async def _ensure_db(self) -> None:
        await init_db()

    async def send_message(
        self,
        to_agent: str,
        content: str,
        from_agent: str = "supervisor",
        metadata: dict | None = None,
    ) -> Message:
        await self._ensure_db()
        msg = Message(
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            metadata=json.dumps(metadata) if metadata else None,
        )
        db = await get_db()
        await db.execute(
            "INSERT INTO messages (message_id, from_agent, to_agent, content, "
            "timestamp, read, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                msg.message_id,
                msg.from_agent,
                msg.to_agent,
                msg.content,
                msg.timestamp,
                0,
                msg.metadata,
            ),
        )
        await db.commit()

        # Enforce max messages per agent
        await self._enforce_limit(to_agent)
        return msg

    async def get_messages(
        self,
        agent: str,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[Message]:
        await self._ensure_db()
        db = await get_db()
        query = "SELECT * FROM messages WHERE to_agent = ?"
        params: list = [agent]
        if unread_only:
            query += " AND read = 0"
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [self._row_to_message(row) for row in rows]

    async def mark_as_read(
        self,
        agent: str,
        message_ids: list[str] | None = None,
    ) -> int:
        await self._ensure_db()
        db = await get_db()
        if message_ids:
            placeholders = ",".join("?" for _ in message_ids)
            cursor = await db.execute(
                f"UPDATE messages SET read = 1 WHERE to_agent = ? "
                f"AND message_id IN ({placeholders})",
                [agent, *message_ids],
            )
        else:
            cursor = await db.execute(
                "UPDATE messages SET read = 1 WHERE to_agent = ? AND read = 0",
                (agent,),
            )
        await db.commit()
        return cursor.rowcount

    async def get_inbox_summary(self, agent: str) -> InboxSummary:
        await self._ensure_db()
        db = await get_db()
        cursor = await db.execute(
            "SELECT COUNT(*) as total FROM messages WHERE to_agent = ?",
            (agent,),
        )
        row = await cursor.fetchone()
        total = row["total"] if row else 0

        cursor = await db.execute(
            "SELECT COUNT(*) as unread FROM messages WHERE to_agent = ? AND read = 0",
            (agent,),
        )
        row = await cursor.fetchone()
        unread = row["unread"] if row else 0

        oldest_unread = None
        if unread > 0:
            cursor = await db.execute(
                "SELECT MIN(timestamp) as oldest FROM messages "
                "WHERE to_agent = ? AND read = 0",
                (agent,),
            )
            row = await cursor.fetchone()
            oldest_unread = row["oldest"] if row else None

        return InboxSummary(
            agent_name=agent,
            total_messages=total,
            unread_count=unread,
            oldest_unread=oldest_unread,
        )

    async def clear_inbox(self, agent: str) -> int:
        await self._ensure_db()
        db = await get_db()
        cursor = await db.execute(
            "DELETE FROM messages WHERE to_agent = ?", (agent,)
        )
        await db.commit()
        return cursor.rowcount

    async def _enforce_limit(self, agent: str) -> None:
        """Delete oldest messages if agent exceeds max limit."""
        db = await get_db()
        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM messages WHERE to_agent = ?",
            (agent,),
        )
        row = await cursor.fetchone()
        count = row["cnt"] if row else 0

        if count > self.max_messages_per_agent:
            excess = count - self.max_messages_per_agent
            await db.execute(
                "DELETE FROM messages WHERE message_id IN ("
                "  SELECT message_id FROM messages WHERE to_agent = ? "
                "  ORDER BY timestamp ASC LIMIT ?"
                ")",
                (agent, excess),
            )
            await db.commit()

    @staticmethod
    def _row_to_message(row) -> Message:
        return Message(
            message_id=row["message_id"],
            from_agent=row["from_agent"],
            to_agent=row["to_agent"],
            content=row["content"],
            timestamp=row["timestamp"],
            read=bool(row["read"]),
            metadata=row["metadata"],
        )


_inbox: AgentInbox | None = None


def get_inbox() -> AgentInbox:
    """Get the global AgentInbox singleton."""
    global _inbox
    if _inbox is None:
        _inbox = AgentInbox()
    return _inbox
