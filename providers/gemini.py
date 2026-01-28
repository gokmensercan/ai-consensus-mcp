"""Gemini CLI provider with FastMCP integration"""

import asyncio
from typing import Annotated

from mcp.server.fastmcp import FastMCP, Context
from mcp.types import ToolAnnotations
from pydantic import Field

from models import AIResponse

# Mini MCP server for Gemini provider (can be mounted)
gemini_mcp = FastMCP("gemini-provider")


class GeminiError(Exception):
    """Gemini-specific error"""

    pass


async def safe_log(ctx: Context | None, message: str) -> None:
    """Safely log a message if context is available."""
    if ctx:
        try:
            await ctx.info(message)
        except (ValueError, AttributeError):
            pass  # Context not available outside request


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
            cwd="/tmp",
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        output = stdout.decode("utf-8").strip()

        if not output and stderr:
            error_msg = stderr.decode("utf-8").strip()
            return AIResponse(
                provider="gemini", response="", success=False, error=error_msg
            )

        return AIResponse(
            provider="gemini", response=output or "(empty)", success=True
        )

    except asyncio.TimeoutError:
        return AIResponse(
            provider="gemini",
            response="",
            success=False,
            error="Timeout (120s)",
        )
    except FileNotFoundError:
        return AIResponse(
            provider="gemini",
            response="",
            success=False,
            error="gemini command not found",
        )
    except Exception as e:
        return AIResponse(
            provider="gemini", response="", success=False, error=str(e)
        )


@gemini_mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        openWorldHint=True,
    ),
)
async def ask_gemini(
    prompt: Annotated[str, Field(description="The prompt to send to Gemini AI")],
    model: Annotated[
        str | None, Field(description="Optional Gemini model (e.g., gemini-2.0-flash)")
    ] = None,
    ctx: Context = None,
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
        return f"Error: {result.error}"
