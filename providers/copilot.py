"""Copilot CLI provider with FastMCP integration"""

from typing import Annotated

from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import CurrentContext
from pydantic import Field

from models import AIResponse
from utils import safe_log
from .subprocess_runner import run_cli_subprocess

# Mini MCP server for Copilot provider (can be mounted)
copilot_mcp = FastMCP("copilot-provider")


async def call_copilot(prompt: str, ctx: Context | None = None) -> AIResponse:
    """
    Call Copilot CLI with the given prompt.

    Args:
        prompt: The prompt to send to Copilot
        ctx: Optional MCP context for logging

    Returns:
        AIResponse with the result
    """
    cmd = ["copilot", "-p", prompt, "--deny-tool", "shell", "--deny-tool", "write"]

    return await run_cli_subprocess(cmd, "copilot", ctx)


@copilot_mcp.tool(
    annotations={
        "readOnlyHint": True,
        "openWorldHint": True,
    },
    tags=["provider", "copilot", "ai"],
)
async def ask_copilot(
    prompt: Annotated[str, Field(description="The prompt to send to Copilot AI")],
    ctx: Context = CurrentContext(),
) -> str:
    """
    Ask Copilot AI a question using local Copilot CLI.
    Returns the AI's response or an error message.
    """
    await safe_log(ctx, f"Processing Copilot query: {prompt[:50]}...")

    result = await call_copilot(prompt, ctx)

    if result.success:
        return result.response
    else:
        raise ToolError(f"Copilot error: {result.error}")
