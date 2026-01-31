#!/usr/bin/env python3
"""
AI Consensus MCP Server

A Model Context Protocol server that provides parallel AI queries
using Gemini CLI, Codex CLI, and Copilot CLI, plus multi-agent orchestration.

Features:
    - Context logging and progress reporting
    - Structured Pydantic output models
    - Tool annotations for better MCP integration
    - Multi-agent orchestration (handoff, assign, messaging)

Tools:
    - ask_gemini: Query Gemini AI
    - ask_codex: Query Codex AI
    - ask_copilot: Query Copilot AI
    - consensus: Query all three in parallel
    - consensus_with_synthesis: Query all three + synthesize
    - council: 3-stage LLM Council pipeline (opinions, peer review, chairman synthesis)
    - agent_handoff: Synchronous agent delegation
    - agent_assign: Asynchronous task assignment
    - check_task: Check async task status
    - list_tasks: List all tasks
    - send_agent_message: Send message to agent inbox
    - read_agent_inbox: Read agent messages
    - inbox_summary: Agent inbox summary
    - list_agents: List registered agents
    - cleanup_tasks: Clean up old tasks
"""

import logging
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import settings

# Configure logging before any other project imports.
# MCP stdio transport uses stdout, so logs must go to stderr.
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

from fastmcp import FastMCP
from tools import register_single_tools, register_consensus_tools, register_orchestration_tools, register_council_tools

# Create MCP server
mcp = FastMCP("ai-consensus")
logger.info("AI Consensus MCP server initialised (log_level=%s)", settings.LOG_LEVEL)

# Register all tools
register_single_tools(mcp)
register_consensus_tools(mcp)
register_orchestration_tools(mcp)
register_council_tools(mcp)


if __name__ == "__main__":
    mcp.run(transport="stdio")
