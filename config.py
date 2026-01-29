"""Configuration management for AI Consensus MCP Server"""

import os
from pathlib import Path


class Config:
    """Central configuration using environment variables with sensible defaults."""

    # Gemini provider settings
    GEMINI_DEFAULT_MODEL: str | None = os.getenv("GEMINI_DEFAULT_MODEL")

    # General settings
    LOG_LEVEL: str = os.getenv("MCP_LOG_LEVEL", "INFO")
    MASK_ERROR_DETAILS: bool = os.getenv("MCP_MASK_ERRORS", "false").lower() == "true"

    # Orchestration settings
    TASK_TIMEOUT_SECONDS: int = int(os.getenv("MCP_TASK_TIMEOUT", "120"))
    TASK_CLEANUP_HOURS: int = int(os.getenv("MCP_TASK_CLEANUP_HOURS", "24"))
    INBOX_MAX_MESSAGES: int = int(os.getenv("MCP_INBOX_MAX_MESSAGES", "100"))
    MAX_HANDOFF_DEPTH: int = int(os.getenv("MCP_MAX_HANDOFF_DEPTH", "10"))
    DB_PATH: str = os.getenv(
        "MCP_DB_PATH",
        str(Path.home() / ".cache" / "ai-consensus-mcp" / "orchestration.db"),
    )


# Global config instance
settings = Config()
