"""Orchestration tools - multi-agent handoff, assign, and messaging"""

from typing import Annotated

from pydantic import Field

from agents import CodexWorkerAgent, CopilotWorkerAgent, GeminiWorkerAgent, get_registry
from models.orchestration import OrchestrationContext, TaskStatus
from orchestration import get_inbox, get_supervisor, get_task_store, init_db


_setup_done = False


async def _ensure_setup() -> None:
    """Lazy initialization of database and agents."""
    global _setup_done
    if _setup_done:
        return

    await init_db()
    registry = get_registry()
    if not await registry.list_agents():
        await registry.register(GeminiWorkerAgent())
        await registry.register(CodexWorkerAgent())
        await registry.register(CopilotWorkerAgent())
    _setup_done = True


def register_orchestration_tools(mcp):
    """Register orchestration tools to the MCP server."""

    # --- Pattern 1: Handoff (sync) ---

    @mcp.tool(
        annotations={
            "readOnlyHint": True,
            "openWorldHint": True,
        },
        tags=["orchestration", "handoff", "sync"],
    )
    async def agent_handoff(
        agent_name: Annotated[
            str,
            Field(description="Name of the agent to hand off to (e.g. 'gemini-worker', 'codex-worker')"),
        ],
        prompt: Annotated[str, Field(description="The prompt to send to the agent")],
        timeout: Annotated[
            int | None,
            Field(description="Timeout in seconds (default: 120)"),
        ] = None,
        current_depth: Annotated[
            int,
            Field(description="Current handoff chain depth for recursion prevention (default: 0)"),
        ] = 0,
    ) -> str:
        """
        Synchronous handoff to a specific agent. Waits for the agent to complete
        and returns the result. Use this when you need an immediate response.
        Pass current_depth to track recursion in chained handoffs.
        """
        await _ensure_setup()

        orch_ctx = OrchestrationContext(
            source_tool="agent_handoff",
            current_depth=current_depth,
        )
        supervisor = get_supervisor()
        result = await supervisor.handoff(
            agent_name=agent_name,
            prompt=prompt,
            timeout=timeout,
            orch_ctx=orch_ctx,
        )

        if result.success:
            return (
                f"## Handoff Result ({result.agent_name})\n\n"
                f"{result.response}\n\n"
                f"---\n"
                f"_Duration: {result.duration_ms}ms | {result.timestamp}_"
            )
        else:
            return (
                f"## Handoff Failed ({result.agent_name})\n\n"
                f"**Error:** {result.error}\n\n"
                f"---\n"
                f"_Duration: {result.duration_ms}ms | {result.timestamp}_"
            )

    # --- Pattern 2: Assign (async) ---

    @mcp.tool(
        annotations={
            "readOnlyHint": False,
            "openWorldHint": True,
        },
        tags=["orchestration", "assign", "async"],
    )
    async def agent_assign(
        agent_name: Annotated[
            str,
            Field(description="Name of the agent to assign the task to"),
        ],
        prompt: Annotated[str, Field(description="The task prompt")],
        timeout: Annotated[
            int | None,
            Field(description="Timeout in seconds (default: 120)"),
        ] = None,
    ) -> str:
        """
        Asynchronously assign a task to an agent. Returns immediately with a task ID.
        Use check_task to poll for results.
        """
        await _ensure_setup()

        orch_ctx = OrchestrationContext(source_tool="agent_assign")
        supervisor = get_supervisor()
        result = await supervisor.assign(
            agent_name=agent_name,
            prompt=prompt,
            timeout=timeout,
            orch_ctx=orch_ctx,
        )

        if result.task_id:
            return (
                f"## Task Assigned\n\n"
                f"- **Task ID:** `{result.task_id}`\n"
                f"- **Agent:** {result.agent_name}\n"
                f"- **Status:** {result.status.value}\n"
                f"- **Message:** {result.message}\n\n"
                f"Use `check_task(\"{result.task_id}\")` to check progress."
            )
        else:
            return f"## Assignment Failed\n\n**Error:** {result.message}"

    @mcp.tool(
        annotations={
            "readOnlyHint": True,
        },
        tags=["orchestration", "assign", "status"],
    )
    async def check_task(
        task_id: Annotated[str, Field(description="The task ID to check")],
    ) -> str:
        """
        Check the status of an async task by its ID.
        Returns current status, result, or error.
        """
        await _ensure_setup()

        store = get_task_store()
        task = await store.get_task(task_id)

        if task is None:
            return f"Task `{task_id}` not found."

        lines = [
            f"## Task Status: `{task.task_id}`\n",
            f"- **Agent:** {task.agent_name}",
            f"- **Status:** {task.status.value}",
            f"- **Created:** {task.created_at}",
        ]

        if task.completed_at:
            lines.append(f"- **Completed:** {task.completed_at}")
        if task.result:
            lines.append(f"\n### Result\n\n{task.result}")
        if task.error:
            lines.append(f"\n### Error\n\n{task.error}")

        return "\n".join(lines)

    @mcp.tool(
        annotations={
            "readOnlyHint": True,
        },
        tags=["orchestration", "assign", "list"],
    )
    async def list_tasks(
        agent_name: Annotated[
            str | None,
            Field(description="Filter by agent name"),
        ] = None,
        status: Annotated[
            str | None,
            Field(description="Filter by status (pending, running, completed, failed, timed_out)"),
        ] = None,
    ) -> str:
        """
        List all orchestration tasks, optionally filtered by agent or status.
        """
        await _ensure_setup()

        store = get_task_store()
        task_status = None
        if status:
            try:
                task_status = TaskStatus(status)
            except ValueError:
                valid = ", ".join(s.value for s in TaskStatus)
                return f"Invalid status '{status}'. Valid values: {valid}"
        tasks = await store.list_tasks(agent_name=agent_name, status=task_status)

        if not tasks:
            return "No tasks found."

        lines = [f"## Tasks ({len(tasks)})\n"]
        for t in tasks:
            status_icon = {
                TaskStatus.PENDING: "⏳",
                TaskStatus.RUNNING: "🔄",
                TaskStatus.COMPLETED: "✅",
                TaskStatus.FAILED: "❌",
                TaskStatus.TIMED_OUT: "⏰",
            }.get(t.status, "❓")
            lines.append(
                f"- {status_icon} `{t.task_id}` | **{t.agent_name}** | "
                f"{t.status.value} | {t.created_at}"
            )

        return "\n".join(lines)

    # --- Pattern 3: Messaging ---

    @mcp.tool(
        annotations={
            "readOnlyHint": False,
        },
        tags=["orchestration", "messaging"],
    )
    async def send_agent_message(
        agent_name: Annotated[
            str,
            Field(description="Target agent name"),
        ],
        content: Annotated[str, Field(description="Message content")],
        from_agent: Annotated[
            str,
            Field(description="Sender name (default: supervisor)"),
        ] = "supervisor",
    ) -> str:
        """
        Send a message to an agent's inbox. Used for passing context or instructions.
        """
        await _ensure_setup()

        supervisor = get_supervisor()
        result = await supervisor.send_message(
            agent_name=agent_name,
            content=content,
            from_agent=from_agent,
        )

        if isinstance(result, str):
            return f"## Send Failed\n\n**Error:** {result}"

        return (
            f"## Message Sent\n\n"
            f"- **ID:** `{result.message_id}`\n"
            f"- **To:** {result.to_agent}\n"
            f"- **From:** {result.from_agent}\n"
            f"- **Time:** {result.timestamp}"
        )

    @mcp.tool(
        annotations={
            "readOnlyHint": True,
        },
        tags=["orchestration", "messaging", "inbox"],
    )
    async def read_agent_inbox(
        agent_name: Annotated[str, Field(description="Agent name to read inbox for")],
        unread_only: Annotated[
            bool,
            Field(description="Only show unread messages (default: False)"),
        ] = False,
        mark_read: Annotated[
            bool,
            Field(description="Mark returned messages as read (default: True)"),
        ] = True,
    ) -> str:
        """
        Read messages from an agent's inbox.
        """
        await _ensure_setup()

        inbox = get_inbox()
        messages = await inbox.get_messages(
            agent=agent_name, unread_only=unread_only
        )

        if not messages:
            return f"No {'unread ' if unread_only else ''}messages for **{agent_name}**."

        if mark_read:
            msg_ids = [m.message_id for m in messages]
            await inbox.mark_as_read(agent_name, msg_ids)

        lines = [f"## Inbox: {agent_name} ({len(messages)} messages)\n"]
        for msg in messages:
            read_icon = "📬" if not msg.read else "📭"
            lines.append(
                f"- {read_icon} `{msg.message_id}` from **{msg.from_agent}** "
                f"({msg.timestamp})\n  > {msg.content[:200]}"
            )

        return "\n".join(lines)

    @mcp.tool(
        annotations={
            "readOnlyHint": True,
        },
        tags=["orchestration", "messaging", "inbox"],
    )
    async def inbox_summary(
        agent_name: Annotated[str, Field(description="Agent name")],
    ) -> str:
        """
        Get a summary of an agent's inbox (total, unread count, oldest unread).
        """
        await _ensure_setup()

        inbox = get_inbox()
        summary = await inbox.get_inbox_summary(agent_name)

        return (
            f"## Inbox Summary: {summary.agent_name}\n\n"
            f"- **Total messages:** {summary.total_messages}\n"
            f"- **Unread:** {summary.unread_count}\n"
            f"- **Oldest unread:** {summary.oldest_unread or 'N/A'}"
        )

    # --- Management ---

    @mcp.tool(
        annotations={
            "readOnlyHint": True,
        },
        tags=["orchestration", "management"],
    )
    async def list_agents() -> str:
        """
        List all registered agents with their capabilities and status.
        """
        await _ensure_setup()

        registry = get_registry()
        agents = await registry.list_agents()

        if not agents:
            return "No agents registered."

        lines = ["## Registered Agents\n"]
        for a in agents:
            caps = ", ".join(c.value for c in a.capabilities)
            lines.append(
                f"- **{a.name}** ({a.agent_type.value}) | "
                f"Status: {a.status} | Capabilities: {caps}"
            )

        return "\n".join(lines)

    @mcp.tool(
        annotations={
            "readOnlyHint": False,
        },
        tags=["orchestration", "management", "cleanup"],
    )
    async def cleanup_tasks(
        max_age_hours: Annotated[
            int,
            Field(description="Delete completed/failed tasks older than this (hours, default: 24)"),
        ] = 24,
    ) -> str:
        """
        Clean up old completed, failed, and timed-out tasks from the database.
        """
        await _ensure_setup()

        store = get_task_store()
        deleted = await store.cleanup_old_tasks(max_age_hours)
        return f"Cleaned up **{deleted}** old task(s) (older than {max_age_hours}h)."
