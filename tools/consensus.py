"""Consensus tools - parallel AI queries with progress reporting"""

import asyncio
from typing import Annotated

from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations
from pydantic import Field

from providers import call_gemini, call_codex
from models import AIResponse, ConsensusResult, SynthesisResult


async def safe_log(ctx: Context | None, message: str) -> None:
    """Safely log a message if context is available."""
    if ctx:
        try:
            await ctx.info(message)
        except (ValueError, AttributeError):
            pass  # Context not available outside request


async def safe_progress(ctx: Context | None, progress: int, total: int = 100) -> None:
    """Safely report progress if context is available."""
    if ctx:
        try:
            await ctx.report_progress(progress=progress, total=total)
        except (ValueError, AttributeError):
            pass  # Context not available outside request


def register_consensus_tools(mcp):
    """Register consensus tools to the MCP server"""

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            openWorldHint=True,
        ),
    )
    async def consensus(
        prompt: Annotated[str, Field(description="The question to ask both AIs")],
        gemini_model: Annotated[
            str | None,
            Field(description="Optional Gemini model (e.g., gemini-2.0-flash)"),
        ] = None,
        ctx: Context = None,
    ) -> str:
        """
        Ask both Gemini and Codex the same question in PARALLEL.
        Returns both responses for comparison with structured output.
        """
        await safe_log(ctx, f"Starting consensus query: {prompt[:50]}...")
        await safe_progress(ctx, 0)

        # Run both in parallel
        gemini_task = asyncio.create_task(call_gemini(prompt, gemini_model, ctx))
        codex_task = asyncio.create_task(call_codex(prompt, ctx))

        await safe_progress(ctx, 10)

        gemini_response, codex_response = await asyncio.gather(
            gemini_task, codex_task, return_exceptions=True
        )

        await safe_progress(ctx, 90)

        # Handle exceptions
        if isinstance(gemini_response, Exception):
            gemini_response = AIResponse(
                provider="gemini",
                response="",
                success=False,
                error=str(gemini_response),
            )
        if isinstance(codex_response, Exception):
            codex_response = AIResponse(
                provider="codex",
                response="",
                success=False,
                error=str(codex_response),
            )

        # Create structured result
        result = ConsensusResult(gemini=gemini_response, codex=codex_response)

        await safe_progress(ctx, 100)
        await safe_log(ctx, "Consensus query completed")

        return result.format_markdown()

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            openWorldHint=True,
        ),
    )
    async def consensus_with_synthesis(
        prompt: Annotated[str, Field(description="The question to ask both AIs")],
        gemini_model: Annotated[
            str | None,
            Field(description="Optional Gemini model (e.g., gemini-2.0-flash)"),
        ] = None,
        ctx: Context = None,
    ) -> str:
        """
        Ask both Gemini and Codex in PARALLEL, then synthesize responses.
        Returns individual responses plus a combined synthesis.
        """
        await safe_log(ctx, f"Starting consensus with synthesis: {prompt[:50]}...")
        await safe_progress(ctx, 0)

        # Get parallel responses
        gemini_task = asyncio.create_task(call_gemini(prompt, gemini_model, ctx))
        codex_task = asyncio.create_task(call_codex(prompt, ctx))

        await safe_progress(ctx, 10)

        gemini_response, codex_response = await asyncio.gather(
            gemini_task, codex_task, return_exceptions=True
        )

        await safe_progress(ctx, 50)

        # Handle exceptions
        if isinstance(gemini_response, Exception):
            gemini_response = AIResponse(
                provider="gemini",
                response="",
                success=False,
                error=str(gemini_response),
            )
        if isinstance(codex_response, Exception):
            codex_response = AIResponse(
                provider="codex",
                response="",
                success=False,
                error=str(codex_response),
            )

        await safe_log(ctx, "Synthesizing responses...")
        await safe_progress(ctx, 60)

        # Ask Gemini to synthesize
        synthesis_prompt = f"""İki farklı AI'dan aynı soru için yanıtlar aldım. Lütfen bunları karşılaştır ve sentezle:

SORU: {prompt}

GEMINI YANITI:
{gemini_response.response if gemini_response.success else f"Error: {gemini_response.error}"}

CODEX YANITI:
{codex_response.response if codex_response.success else f"Error: {codex_response.error}"}

Lütfen:
1. Ortak noktaları belirt
2. Farklılıkları belirt
3. En iyi yaklaşımı öner"""

        synthesis_response = await call_gemini(synthesis_prompt, gemini_model, ctx)

        await safe_progress(ctx, 100)
        await safe_log(ctx, "Synthesis completed")

        # Create structured result
        result = SynthesisResult(
            gemini=gemini_response,
            codex=codex_response,
            synthesis=synthesis_response,
        )

        return result.format_markdown()
