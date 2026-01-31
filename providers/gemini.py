"""Gemini CLI provider with FastMCP integration"""

from typing import Annotated

from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import CurrentContext
from pydantic import Field

from models import AIResponse
from utils import safe_log
from .subprocess_runner import run_cli_subprocess

# Mini MCP server for Gemini provider (can be mounted)
gemini_mcp = FastMCP("gemini-provider")


async def call_gemini(
    prompt: str, model: str | None = None, ctx: Context | None = None
) -> AIResponse:
    """
    Call Gemini CLI with the given prompt.

    Args:
        prompt: The prompt to send to Gemini
        model: Optional model (e.g., gemini-2.0-flash)
        ctx: Optional MCP context for logging

    Returns:
        AIResponse with the result
    """
    cmd = ["gemini", "-p", prompt, "-o", "text"]
    if model:
        cmd.extend(["-m", model])

    return await run_cli_subprocess(cmd, "gemini", ctx)


@gemini_mcp.tool(
    annotations={
        "readOnlyHint": True,
        "openWorldHint": True,
    },
    tags=["provider", "gemini", "ai"],
)
async def ask_gemini(
    prompt: Annotated[str, Field(description="The prompt to send to Gemini AI")],
    model: Annotated[
        str | None, Field(description="Optional Gemini model (e.g., gemini-2.0-flash)")
    ] = None,
    ctx: Context = CurrentContext(),
) -> str:
    """
    Ask Gemini AI a question using local Gemini CLI.
    Returns the AI's response or an error message.
    """
    await safe_log(ctx, f"Processing Gemini query: {prompt[:50]}...")

    result = await call_gemini(prompt, model, ctx)

    if result.success:
        return result.response
    else:
        raise ToolError(f"Gemini error: {result.error}")
