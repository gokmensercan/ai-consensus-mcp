"""SQLite database connection and schema management for orchestration"""

from pathlib import Path

import aiosqlite

from config import settings

_db: aiosqlite.Connection | None = None
_initialized = False


def _get_db_path() -> Path:
    path = Path(settings.DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


async def get_db() -> aiosqlite.Connection:
    """Get or create the singleton database connection."""
    global _db
    if _db is None:
        db_path = _get_db_path()
        _db = await aiosqlite.connect(str(db_path))
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA foreign_keys=ON")
    return _db


async def init_db() -> None:
    """Initialize database tables and clean up orphan tasks."""
    global _initialized
    if _initialized:
        return

    db = await get_db()

    await db.executescript(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            agent_name TEXT NOT NULL,
            prompt TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            result TEXT,
            error TEXT,
            timeout_seconds INTEGER DEFAULT 120,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            orch_context TEXT
        );

        CREATE TABLE IF NOT EXISTS messages (
            message_id TEXT PRIMARY KEY,
            from_agent TEXT NOT NULL,
            to_agent TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            read INTEGER DEFAULT 0,
            metadata TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
        CREATE INDEX IF NOT EXISTS idx_tasks_agent ON tasks(agent_name);
        CREATE INDEX IF NOT EXISTS idx_messages_to ON messages(to_agent);
        CREATE INDEX IF NOT EXISTS idx_messages_read ON messages(to_agent, read);
        """
    )

    # Mark orphan RUNNING/PENDING tasks as FAILED on startup
    await db.execute(
        "UPDATE tasks SET status = 'failed', error = 'Server restarted' "
        "WHERE status IN ('running', 'pending')"
    )
    await db.commit()
    _initialized = True


async def close_db() -> None:
    """Close the database connection."""
    global _db, _initialized
    if _db is not None:
        await _db.close()
        _db = None
        _initialized = False
