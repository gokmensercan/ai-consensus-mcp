"""Configuration management for AI Consensus MCP Server"""

import os


class Config:
    """Central configuration using environment variables with sensible defaults."""

    # Gemini provider settings
    GEMINI_CWD: str = os.getenv("GEMINI_CWD", "/tmp")
    GEMINI_DEFAULT_MODEL: str | None = os.getenv("GEMINI_DEFAULT_MODEL")

    # Codex provider settings
    CODEX_CWD: str = os.getenv("CODEX_CWD", "/tmp/codex-workspace")

    # General settings
    LOG_LEVEL: str = os.getenv("MCP_LOG_LEVEL", "INFO")
    MASK_ERROR_DETAILS: bool = os.getenv("MCP_MASK_ERRORS", "false").lower() == "true"


# Global config instance
settings = Config()
