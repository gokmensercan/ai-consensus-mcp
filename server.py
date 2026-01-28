#!/usr/bin/env python3
"""
AI Consensus MCP Server

A Model Context Protocol server that provides parallel AI queries
using Gemini CLI and Codex CLI.

Features:
    - Context logging and progress reporting
    - Structured Pydantic output models
    - Tool annotations for better MCP integration

Tools:
    - ask_gemini: Query Gemini AI
    - ask_codex: Query Codex AI
    - consensus: Query both in parallel
    - consensus_with_synthesis: Query both + synthesize
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from fastmcp import FastMCP
from tools import register_single_tools, register_consensus_tools

# Create MCP server
mcp = FastMCP("ai-consensus")

# Register all tools
register_single_tools(mcp)
register_consensus_tools(mcp)


if __name__ == "__main__":
    mcp.run(transport="stdio")
