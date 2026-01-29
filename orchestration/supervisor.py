"""Supervisor - orchestrates agents via handoff, assign, and messaging patterns"""

import asyncio
import logging
import time

from agents.registry import get_registry
from config import settings
from models.orchestration import (
    AssignResult,
    HandoffResult,
    Message,
    OrchestrationContext,
    TaskStatus,
)

from .inbox import get_inbox
from .task_store import get_task_store

logger = logging.getLogger(__name__)

MAX_HANDOFF_DEPTH = settings.MAX_HANDOFF_DEPTH


def _mask_error(error: str) -> str:
    """Mask error details if configured."""
    if settings.MASK_ERROR_DETAILS:
        return "An internal error occurred"
    return error


class Supervisor:
    """Orchestrates agent execution using three patterns."""

    # --- Pattern 1: Handoff (synchronous) ---

    async def handoff(
        self,
        agent_name: str,
        prompt: str,
        timeout: int | None = None,
        orch_ctx: OrchestrationContext | None = None,
    ) -> HandoffResult:
        if orch_ctx is None:
            orch_ctx = OrchestrationContext(source_tool="agent_handoff")

        if orch_ctx.current_depth > MAX_HANDOFF_DEPTH:
            return HandoffResult(
                agent_name=agent_name,
                prompt=prompt,
                success=False,
                error=f"Max handoff depth ({MAX_HANDOFF_DEPTH}) exceeded",
            )

        timeout = timeout or settings.TASK_TIMEOUT_SECONDS
        registry = get_registry()
        agent = await registry.get(agent_name)

        if agent is None:
            return HandoffResult(
                agent_name=agent_name,
                prompt=prompt,
                success=False,
                error=f"Agent '{agent_name}' not found",
            )

        start = time.monotonic()
        try:
            result = await asyncio.wait_for(
                agent.execute(prompt, orch_ctx=orch_ctx),
                timeout=timeout,
            )
            elapsed_ms = int((time.monotonic() - start) * 1000)

            if result.success:
                return HandoffResult(
                    agent_name=agent_name,
                    prompt=prompt,
                    response=result.response,
                    success=True,
                    duration_ms=elapsed_ms,
                )
            else:
                return HandoffResult(
                    agent_name=agent_name,
                    prompt=prompt,
                    success=False,
                    error=result.error or "Agent returned failure",
                    duration_ms=elapsed_ms,
                )
        except asyncio.TimeoutError:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return HandoffResult(
                agent_name=agent_name,
                prompt=prompt,
                success=False,
                error=f"Handoff timed out after {timeout}s",
                duration_ms=elapsed_ms,
            )
        except Exception as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.error("Handoff to %s failed: %s", agent_name, e, exc_info=True)
            return HandoffResult(
                agent_name=agent_name,
                prompt=prompt,
                success=False,
                error=_mask_error(str(e)),
                duration_ms=elapsed_ms,
            )

    # --- Pattern 2: Assign (asynchronous) ---

    async def assign(
        self,
        agent_name: str,
        prompt: str,
        timeout: int | None = None,
        orch_ctx: OrchestrationContext | None = None,
    ) -> AssignResult:
        timeout = timeout or settings.TASK_TIMEOUT_SECONDS
        registry = get_registry()
        agent = await registry.get(agent_name)

        if agent is None:
            return AssignResult(
                task_id="",
                agent_name=agent_name,
                status=TaskStatus.FAILED,
                message=f"Agent '{agent_name}' not found",
            )

        if orch_ctx is None:
            orch_ctx = OrchestrationContext(source_tool="agent_assign")

        store = get_task_store()
        task = await store.create_task(
            agent_name=agent_name,
            prompt=prompt,
            orch_ctx=orch_ctx,
            timeout=timeout,
        )

        # Fire-and-forget
        asyncio.create_task(
            self._safe_run_task(task.task_id, agent, prompt, orch_ctx, timeout)
        )

        return AssignResult(
            task_id=task.task_id,
            agent_name=agent_name,
            status=TaskStatus.PENDING,
            message=f"Task {task.task_id} assigned to {agent_name}",
        )

    async def _safe_run_task(
        self,
        task_id: str,
        agent,
        prompt: str,
        orch_ctx: OrchestrationContext | None,
        timeout: int,
    ) -> None:
        """Safe wrapper for background task execution."""
        store = get_task_store()
        try:
            await store.update_status(task_id, TaskStatus.RUNNING)
            result = await asyncio.wait_for(
                agent.execute(prompt, orch_ctx=orch_ctx),
                timeout=timeout,
            )
            if result.success:
                await store.update_status(
                    task_id, TaskStatus.COMPLETED, result=result.response
                )
            else:
                await store.update_status(
                    task_id,
                    TaskStatus.FAILED,
                    error=result.error or "Agent returned failure",
                )
        except asyncio.TimeoutError:
            await store.update_status(
                task_id,
                TaskStatus.TIMED_OUT,
                error=f"Task timed out after {timeout}s",
            )
        except Exception as e:
            logger.error("Task %s failed: %s", task_id, e, exc_info=True)
            await store.update_status(
                task_id, TaskStatus.FAILED, error=_mask_error(str(e))
            )

    # --- Pattern 3: Send Message ---

    async def send_message(
        self,
        agent_name: str,
        content: str,
        from_agent: str = "supervisor",
        metadata: dict | None = None,
    ) -> Message | str:
        registry = get_registry()
        agent = await registry.get(agent_name)
        if agent is None:
            return f"Agent '{agent_name}' not found"

        inbox = get_inbox()
        return await inbox.send_message(
            to_agent=agent_name,
            content=content,
            from_agent=from_agent,
            metadata=metadata,
        )


_supervisor: Supervisor | None = None


def get_supervisor() -> Supervisor:
    """Get the global Supervisor singleton."""
    global _supervisor
    if _supervisor is None:
        _supervisor = Supervisor()
    return _supervisor
