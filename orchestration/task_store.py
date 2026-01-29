"""SQLite-backed task store for async agent tasks"""

from datetime import datetime, timedelta, timezone

from models.orchestration import AgentTask, OrchestrationContext, TaskStatus

from .database import get_db, init_db


class TaskStore:
    """Manages async task lifecycle in SQLite."""

    async def _ensure_db(self) -> None:
        await init_db()

    async def create_task(
        self,
        agent_name: str,
        prompt: str,
        orch_ctx: OrchestrationContext | None = None,
        timeout: int = 120,
    ) -> AgentTask:
        await self._ensure_db()
        task = AgentTask(
            agent_name=agent_name,
            prompt=prompt,
            timeout_seconds=timeout,
            orch_context=orch_ctx.model_dump_json() if orch_ctx else None,
        )
        db = await get_db()
        await db.execute(
            "INSERT INTO tasks (task_id, agent_name, prompt, status, timeout_seconds, "
            "created_at, orch_context) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                task.task_id,
                task.agent_name,
                task.prompt,
                task.status.value,
                task.timeout_seconds,
                task.created_at,
                task.orch_context,
            ),
        )
        await db.commit()
        return task

    async def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        result: str | None = None,
        error: str | None = None,
    ) -> AgentTask | None:
        await self._ensure_db()
        db = await get_db()
        completed_at = (
            datetime.now(timezone.utc).isoformat()
            if status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.TIMED_OUT)
            else None
        )
        await db.execute(
            "UPDATE tasks SET status = ?, result = ?, error = ?, completed_at = ? "
            "WHERE task_id = ?",
            (status.value, result, error, completed_at, task_id),
        )
        await db.commit()
        return await self.get_task(task_id)

    async def get_task(self, task_id: str) -> AgentTask | None:
        await self._ensure_db()
        db = await get_db()
        cursor = await db.execute(
            "SELECT * FROM tasks WHERE task_id = ?", (task_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_task(row)

    async def list_tasks(
        self,
        agent_name: str | None = None,
        status: TaskStatus | None = None,
    ) -> list[AgentTask]:
        await self._ensure_db()
        db = await get_db()
        query = "SELECT * FROM tasks WHERE 1=1"
        params: list = []
        if agent_name:
            query += " AND agent_name = ?"
            params.append(agent_name)
        if status:
            query += " AND status = ?"
            params.append(status.value)
        query += " ORDER BY created_at DESC"
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [self._row_to_task(row) for row in rows]

    async def cleanup_old_tasks(self, max_age_hours: int = 24) -> int:
        await self._ensure_db()
        db = await get_db()
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=max_age_hours)).isoformat()
        cursor = await db.execute(
            "DELETE FROM tasks WHERE created_at < ? AND status IN (?, ?, ?)",
            (cutoff, TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.TIMED_OUT.value),
        )
        await db.commit()
        return cursor.rowcount

    @staticmethod
    def _row_to_task(row) -> AgentTask:
        return AgentTask(
            task_id=row["task_id"],
            agent_name=row["agent_name"],
            prompt=row["prompt"],
            status=TaskStatus(row["status"]),
            result=row["result"],
            error=row["error"],
            timeout_seconds=row["timeout_seconds"],
            created_at=row["created_at"],
            completed_at=row["completed_at"],
            orch_context=row["orch_context"],
        )


_task_store: TaskStore | None = None


def get_task_store() -> TaskStore:
    """Get the global TaskStore singleton."""
    global _task_store
    if _task_store is None:
        _task_store = TaskStore()
    return _task_store
