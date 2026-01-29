#!/usr/bin/env python3
"""
AI Consensus MCP Server

A Model Context Protocol server that provides parallel AI queries
using Gemini CLI and Codex CLI, plus multi-agent orchestration.

Features:
    - Context logging and progress reporting
    - Structured Pydantic output models
    - Tool annotations for better MCP integration
    - Multi-agent orchestration (handoff, assign, messaging)

Tools:
    - ask_gemini: Query Gemini AI
    - ask_codex: Query Codex AI
    - consensus: Query both in parallel
    - consensus_with_synthesis: Query both + synthesize
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

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from fastmcp import FastMCP
from tools import register_single_tools, register_consensus_tools, register_orchestration_tools

# Create MCP server
mcp = FastMCP("ai-consensus")

# Register all tools
register_single_tools(mcp)
register_consensus_tools(mcp)
register_orchestration_tools(mcp)


if __name__ == "__main__":
    mcp.run(transport="stdio")
