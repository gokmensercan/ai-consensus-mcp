"""Codex worker agent for orchestration system"""

import logging

from models.orchestration import AgentCapability, AgentType, OrchestrationContext
from models.responses import AIResponse
from providers import call_codex

from .base import BaseAgent

logger = logging.getLogger(__name__)


class CodexWorkerAgent(BaseAgent):
    """Worker agent that delegates to Codex CLI."""

    def __init__(self):
        super().__init__(
            name="codex-worker",
            agent_type=AgentType.CODEX,
            capabilities=[
                AgentCapability.GENERAL_QA,
                AgentCapability.CODE_GENERATION,
                AgentCapability.CODE_REVIEW,
            ],
        )

    async def execute(
        self,
        prompt: str,
        orch_ctx: OrchestrationContext | None = None,
        **kwargs,
    ) -> AIResponse:
        self.set_status("busy")
        try:
            if orch_ctx:
                logger.info(
                    "CodexWorker executing [request_id=%s, source=%s, depth=%d]",
                    orch_ctx.request_id,
                    orch_ctx.source_tool,
                    orch_ctx.current_depth,
                )
            result = await call_codex(prompt, ctx=None)
            return result
        finally:
            self.set_status("idle")
