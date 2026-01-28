"""Single AI query tools with FastMCP best practices"""

from typing import Annotated

from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations
from pydantic import Field

from providers import call_gemini, call_codex


async def safe_log(ctx: Context | None, message: str) -> None:
    """Safely log a message if context is available."""
    if ctx:
        try:
            await ctx.info(message)
        except (ValueError, AttributeError):
            pass  # Context not available outside request


def register_single_tools(mcp):
    """Register single-AI query tools to the MCP server"""

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            openWorldHint=True,
        ),
    )
    async def ask_gemini(
        prompt: Annotated[str, Field(description="The prompt to send to Gemini AI")],
        model: Annotated[
            str | None,
            Field(description="Optional Gemini model (e.g., gemini-2.0-flash)"),
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

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            openWorldHint=True,
        ),
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
