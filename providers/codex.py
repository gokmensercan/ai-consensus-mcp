"""Codex CLI provider with FastMCP integration"""

import asyncio
from typing import Annotated

from fastmcp import FastMCP, Context
from pydantic import Field

from models import AIResponse

# Mini MCP server for Codex provider (can be mounted)
codex_mcp = FastMCP("codex-provider")


class CodexError(Exception):
    """Codex-specific error"""

    pass


async def safe_log(ctx: Context | None, message: str) -> None:
    """Safely log a message if context is available."""
    if ctx and ctx.request_context is not None:
        try:
            await ctx.info(message)
        except (ValueError, AttributeError, RuntimeError):
            pass  # Context not available outside request


async def call_codex(prompt: str, ctx: Context | None = None) -> AIResponse:
    """
    Call Codex CLI with the given prompt.

    Args:
        prompt: The prompt to send to Codex
        ctx: Optional MCP context for logging

    Returns:
        AIResponse with the result
    """
    cmd = ["codex", "exec", "--skip-git-repo-check", prompt]

    await safe_log(ctx, "Calling Codex CLI...")

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
                provider="codex", response="", success=False, error=error_msg
            )

        return AIResponse(provider="codex", response=output or "(empty)", success=True)

    except asyncio.TimeoutError:
        return AIResponse(
            provider="codex",
            response="",
            success=False,
            error="Timeout (120s)",
        )
    except FileNotFoundError:
        return AIResponse(
            provider="codex",
            response="",
            success=False,
            error="codex command not found",
        )
    except Exception as e:
        return AIResponse(provider="codex", response="", success=False, error=str(e))


@codex_mcp.tool(
    annotations={
        "readOnlyHint": True,
        "openWorldHint": True,
    },
)
async def ask_codex(
    prompt: Annotated[str, Field(description="The prompt to send to Codex AI")],
    ctx: Context = None,
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
        return f"Error: {result.error}"
