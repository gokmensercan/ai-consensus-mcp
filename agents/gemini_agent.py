"""Gemini worker agent for orchestration system"""

import logging

from models.orchestration import AgentCapability, AgentType, OrchestrationContext
from models.responses import AIResponse
from providers import call_gemini

from .base import BaseAgent

logger = logging.getLogger(__name__)


class GeminiWorkerAgent(BaseAgent):
    """Worker agent that delegates to Gemini CLI."""

    def __init__(self, model: str | None = None):
        super().__init__(
            name="gemini-worker",
            agent_type=AgentType.GEMINI,
            capabilities=[
                AgentCapability.GENERAL_QA,
                AgentCapability.CODE_GENERATION,
                AgentCapability.SYNTHESIS,
            ],
        )
        self.model = model

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
                    "GeminiWorker executing [request_id=%s, source=%s, depth=%d]",
                    orch_ctx.request_id,
                    orch_ctx.source_tool,
                    orch_ctx.current_depth,
                )
            model = kwargs.get("model", self.model)
            result = await call_gemini(prompt, model, ctx=None)
            return result
        finally:
            self.set_status("idle")
