"""Pydantic models for multi-agent orchestration system"""

import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    """Supported agent types"""

    GEMINI = "gemini"
    CODEX = "codex"
    COPILOT = "copilot"


class AgentCapability(str, Enum):
    """Agent capabilities"""

    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    GENERAL_QA = "general_qa"
    SYNTHESIS = "synthesis"


class AgentInfo(BaseModel):
    """Agent registration info"""

    name: str = Field(description="Unique agent name")
    agent_type: AgentType = Field(description="Agent type")
    capabilities: list[AgentCapability] = Field(description="Agent capabilities")
    status: str = Field(default="idle", description="Current agent status")


class TaskStatus(str, Enum):
    """Task lifecycle status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


class AgentTask(BaseModel):
    """Async task assigned to an agent"""

    task_id: str = Field(
        default_factory=lambda: uuid.uuid4().hex[:12],
        description="Unique task identifier",
    )
    agent_name: str = Field(description="Target agent name")
    prompt: str = Field(description="Task prompt")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Task status")
    result: str | None = Field(default=None, description="Task result")
    error: str | None = Field(default=None, description="Error message if failed")
    timeout_seconds: int = Field(default=120, description="Task timeout in seconds")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Creation timestamp",
    )
    completed_at: str | None = Field(
        default=None, description="Completion timestamp"
    )
    orch_context: str | None = Field(
        default=None, description="JSON serialized OrchestrationContext"
    )


class Message(BaseModel):
    """Inter-agent message"""

    message_id: str = Field(
        default_factory=lambda: uuid.uuid4().hex[:12],
        description="Unique message identifier",
    )
    from_agent: str = Field(description="Sender agent name")
    to_agent: str = Field(description="Recipient agent name")
    content: str = Field(description="Message content")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Message timestamp",
    )
    read: bool = Field(default=False, description="Whether the message has been read")
    metadata: str | None = Field(
        default=None, description="Optional JSON metadata"
    )


class InboxSummary(BaseModel):
    """Summary of an agent's inbox"""

    agent_name: str = Field(description="Agent name")
    total_messages: int = Field(description="Total messages in inbox")
    unread_count: int = Field(description="Unread message count")
    oldest_unread: str | None = Field(
        default=None, description="Timestamp of oldest unread message"
    )


class HandoffResult(BaseModel):
    """Result of a synchronous handoff"""

    agent_name: str = Field(description="Agent that handled the request")
    prompt: str = Field(description="The prompt sent")
    response: str = Field(default="", description="Agent response")
    success: bool = Field(description="Whether the handoff succeeded")
    error: str | None = Field(default=None, description="Error message if failed")
    duration_ms: int = Field(default=0, description="Execution duration in ms")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Handoff timestamp",
    )


class AssignResult(BaseModel):
    """Result of an async task assignment"""

    task_id: str = Field(description="Assigned task ID")
    agent_name: str = Field(description="Agent the task was assigned to")
    status: TaskStatus = Field(description="Initial task status")
    message: str = Field(description="Status message")


class OrchestrationContext(BaseModel):
    """Context preserved across background tasks for metadata tracking"""

    request_id: str = Field(
        default_factory=lambda: uuid.uuid4().hex[:12],
        description="Unique request identifier",
    )
    session_id: str | None = Field(
        default=None, description="MCP session identifier"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Context creation timestamp",
    )
    source_tool: str | None = Field(
        default=None, description="Tool that originated this context"
    )
    current_depth: int = Field(
        default=0, description="Current handoff recursion depth"
    )
