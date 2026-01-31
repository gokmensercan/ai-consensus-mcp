"""Codex CLI provider with FastMCP integration"""

from typing import Annotated

from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import CurrentContext
from pydantic import Field

from models import AIResponse
from utils import safe_log
from .subprocess_runner import run_cli_subprocess

# Mini MCP server for Codex provider (can be mounted)
codex_mcp = FastMCP("codex-provider")


async def call_codex(prompt: str, ctx: Context | None = None) -> AIResponse:
    """
    Call Codex CLI with the given prompt.

    Args:
        prompt: The prompt to send to Codex
        ctx: Optional MCP context for logging

    Returns:
        AIResponse with the result
    """
    cmd = ["codex", "exec", prompt]

    return await run_cli_subprocess(cmd, "codex", ctx)


@codex_mcp.tool(
    annotations={
        "readOnlyHint": True,
        "openWorldHint": True,
    },
    tags=["provider", "codex", "ai"],
)
async def ask_codex(
    prompt: Annotated[str, Field(description="The prompt to send to Codex AI")],
    ctx: Context = CurrentContext(),
) -> str:
    """
    Ask Codex AI a question using local Codex CLI.
    Returns the AI's response or an error message.
    """
    await safe_log(ctx, f"Processing Codex query: {prompt[:50]}...")

    result = await call_codex(prompt, ctx)

    if result.success:
        return result.response
    else:
        raise ToolError(f"Codex error: {result.error}")
