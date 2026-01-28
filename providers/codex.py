"""Codex CLI provider with FastMCP integration"""

import asyncio
from typing import Annotated

from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import CurrentContext
from pydantic import Field

from config import settings
from models import AIResponse
from utils import safe_log

# Mini MCP server for Codex provider (can be mounted)
codex_mcp = FastMCP("codex-provider")


class CodexError(Exception):
    """Codex-specific error"""

    pass


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

    await safe_log(ctx, "Calling Codex CLI...")

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=settings.CODEX_CWD,
        )
        stdout, stderr = await proc.communicate()
        output = stdout.decode("utf-8").strip()

        if not output and stderr:
            error_msg = stderr.decode("utf-8").strip()
            return AIResponse(
                provider="codex", response="", success=False, error=error_msg
            )

        return AIResponse(provider="codex", response=output or "(empty)", success=True)

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
