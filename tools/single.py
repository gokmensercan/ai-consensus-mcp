"""Single AI query tools with FastMCP best practices"""

from typing import Annotated

from fastmcp import Context
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import CurrentContext
from pydantic import Field

from providers import call_gemini, call_codex
from utils import safe_log


def register_single_tools(mcp):
    """Register single-AI query tools to the MCP server"""

    @mcp.tool(
        annotations={
            "readOnlyHint": True,
            "openWorldHint": True,
        },
        tags=["provider", "gemini", "ai", "single"],
    )
    async def ask_gemini(
        prompt: Annotated[str, Field(description="The prompt to send to Gemini AI")],
        model: Annotated[
            str | None,
            Field(description="Optional Gemini model (e.g., gemini-2.0-flash)"),
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

    @mcp.tool(
        annotations={
            "readOnlyHint": True,
            "openWorldHint": True,
        },
        tags=["provider", "codex", "ai", "single"],
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
