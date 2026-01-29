"""Agent registry - singleton for managing registered agents"""

import asyncio

from models.orchestration import AgentCapability, AgentInfo

from .base import BaseAgent


class AgentRegistry:
    """Thread-safe registry for worker agents."""

    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}
        self._lock = asyncio.Lock()

    async def register(self, agent: BaseAgent) -> None:
        async with self._lock:
            self._agents[agent.name] = agent

    async def get(self, name: str) -> BaseAgent | None:
        async with self._lock:
            return self._agents.get(name)

    async def list_agents(self) -> list[AgentInfo]:
        async with self._lock:
            return [agent.info for agent in self._agents.values()]

    async def get_by_capability(
        self, capability: AgentCapability
    ) -> list[AgentInfo]:
        async with self._lock:
            return [
                agent.info
                for agent in self._agents.values()
                if capability in agent.capabilities
            ]


_registry: AgentRegistry | None = None


def get_registry() -> AgentRegistry:
    """Get the global AgentRegistry singleton."""
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry
