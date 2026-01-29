"""Gemini CLI provider with FastMCP integration"""

import asyncio
from typing import Annotated

from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import CurrentContext
from pydantic import Field

from models import AIResponse
from utils import safe_log

# Mini MCP server for Gemini provider (can be mounted)
gemini_mcp = FastMCP("gemini-provider")


class GeminiError(Exception):
    """Gemini-specific error"""

    pass


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

    await safe_log(ctx, "Calling Gemini CLI...")

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        output = stdout.decode("utf-8").strip()

        if not output and stderr:
            error_msg = stderr.decode("utf-8").strip()
            return AIResponse(
                provider="gemini", response="", success=False, error=error_msg
            )

        return AIResponse(
            provider="gemini", response=output or "(empty)", success=True
        )

    except FileNotFoundError as e:
        return AIResponse(
            provider="gemini",
            response="",
            success=False,
            error=f"gemini command not found: {e}",
        )
    except Exception as e:
        return AIResponse(
            provider="gemini", response="", success=False, error=str(e)
        )


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
