"""Copilot worker agent for orchestration system"""

import logging

from models.orchestration import AgentCapability, AgentType, OrchestrationContext
from models.responses import AIResponse
from providers import call_copilot

from .base import BaseAgent

logger = logging.getLogger(__name__)


class CopilotWorkerAgent(BaseAgent):
    """Worker agent that delegates to Copilot CLI."""

    def __init__(self):
        super().__init__(
            name="copilot-worker",
            agent_type=AgentType.COPILOT,
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
                    "CopilotWorker executing [request_id=%s, source=%s, depth=%d]",
                    orch_ctx.request_id,
                    orch_ctx.source_tool,
                    orch_ctx.current_depth,
                )
            result = await call_copilot(prompt, ctx=None)
            return result
        finally:
            self.set_status("idle")
