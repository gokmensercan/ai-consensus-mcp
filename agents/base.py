"""Base agent abstract class for orchestration system"""

from abc import ABC, abstractmethod

from models.orchestration import (
    AgentCapability,
    AgentInfo,
    AgentType,
    OrchestrationContext,
)
from models.responses import AIResponse


class BaseAgent(ABC):
    """Abstract base class for all worker agents."""

    def __init__(
        self,
        name: str,
        agent_type: AgentType,
        capabilities: list[AgentCapability],
    ):
        self.name = name
        self.agent_type = agent_type
        self.capabilities = capabilities
        self._status = "idle"

    @abstractmethod
    async def execute(
        self,
        prompt: str,
        orch_ctx: OrchestrationContext | None = None,
        **kwargs,
    ) -> AIResponse:
        """Execute a prompt and return an AIResponse."""
        ...

    def set_status(self, status: str) -> None:
        self._status = status

    @property
    def info(self) -> AgentInfo:
        return AgentInfo(
            name=self.name,
            agent_type=self.agent_type,
            capabilities=self.capabilities,
            status=self._status,
        )
