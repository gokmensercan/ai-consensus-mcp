"""Consensus tools - parallel AI queries with progress reporting and caching"""

import asyncio
from typing import Annotated

from fastmcp import Context
from fastmcp.server.dependencies import CurrentContext
from pydantic import Field

from providers import call_gemini, call_codex
from models import AIResponse, ConsensusResult, SynthesisResult
from utils import (
    safe_log,
    safe_progress,
    cache_consensus_result,
    get_cached_result,
    get_last_result,
    clear_cache,
)


def register_consensus_tools(mcp):
    """Register consensus tools to the MCP server"""

    @mcp.tool(
        annotations={
            "readOnlyHint": True,
            "openWorldHint": True,
        },
        tags=["consensus", "parallel", "ai"],
        # task=True disabled - Context (Session State) incompatible with background tasks
    )
    async def consensus(
        prompt: Annotated[str, Field(description="The question to ask both AIs")],
        gemini_model: Annotated[
            str | None,
            Field(description="Optional Gemini model (e.g., gemini-2.0-flash)"),
        ] = None,
        use_cache: Annotated[
            bool,
            Field(description="Use cached result if available (default: True)"),
        ] = True,
        ctx: Context = CurrentContext(),
    ) -> str:
        """
        Ask both Gemini and Codex the same question in PARALLEL.
        Returns both responses for comparison with structured output.
        Results are cached in session state for quick retrieval.
        """
        await safe_log(ctx, f"Starting consensus query: {prompt[:50]}...")
        await safe_progress(ctx, 0)

        # Check cache first
        if use_cache:
            cached = await get_cached_result(ctx, prompt)
            if cached and isinstance(cached, ConsensusResult):
                await safe_log(ctx, "Returning cached result")
                await safe_progress(ctx, 100)
                return f"[CACHED]\n\n{cached.format_markdown()}"

        await safe_progress(ctx, 5)

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

        # Cache the result
        await cache_consensus_result(ctx, prompt, result)

        await safe_progress(ctx, 100)
        await safe_log(ctx, "Consensus query completed and cached")

        return result.format_markdown()

    @mcp.tool(
        annotations={
            "readOnlyHint": True,
            "openWorldHint": True,
        },
        tags=["consensus", "parallel", "ai", "synthesis"],
        # task=True disabled - Context (Session State) incompatible with background tasks
    )
    async def consensus_with_synthesis(
        prompt: Annotated[str, Field(description="The question to ask both AIs")],
        gemini_model: Annotated[
            str | None,
            Field(description="Optional Gemini model (e.g., gemini-2.0-flash)"),
        ] = None,
        use_cache: Annotated[
            bool,
            Field(description="Use cached result if available (default: True)"),
        ] = True,
        ctx: Context = CurrentContext(),
    ) -> str:
        """
        Ask both Gemini and Codex in PARALLEL, then synthesize responses.
        Returns individual responses plus a combined synthesis.
        Results are cached in session state for quick retrieval.
        """
        await safe_log(ctx, f"Starting consensus with synthesis: {prompt[:50]}...")
        await safe_progress(ctx, 0)

        # Check cache first
        if use_cache:
            cached = await get_cached_result(ctx, prompt)
            if cached and isinstance(cached, SynthesisResult):
                await safe_log(ctx, "Returning cached synthesis result")
                await safe_progress(ctx, 100)
                return f"[CACHED]\n\n{cached.format_markdown()}"

        await safe_progress(ctx, 5)

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

        await safe_progress(ctx, 95)

        # Create structured result
        result = SynthesisResult(
            gemini=gemini_response,
            codex=codex_response,
            synthesis=synthesis_response,
        )

        # Cache the result
        await cache_consensus_result(ctx, prompt, result)

        await safe_progress(ctx, 100)
        await safe_log(ctx, "Synthesis completed and cached")

        return result.format_markdown()

    @mcp.tool(
        annotations={
            "readOnlyHint": True,
        },
        tags=["consensus", "cache", "session"],
    )
    async def get_last_consensus(
        ctx: Context = CurrentContext(),
    ) -> str:
        """
        Get the last consensus query result from session cache.
        Useful for retrieving previous results without re-running queries.
        """
        result = await get_last_result(ctx)

        if result is None:
            return "No cached consensus results found in this session."

        prompt = result["prompt"]
        result_type = result["type"]
        data = result["data"]

        if result_type == "synthesis":
            parsed = SynthesisResult.model_validate(data)
        else:
            parsed = ConsensusResult.model_validate(data)

        return f"**Last Query:** {prompt}\n\n{parsed.format_markdown()}"

    @mcp.tool(
        annotations={
            "readOnlyHint": False,
        },
        tags=["consensus", "cache", "session"],
    )
    async def clear_consensus_cache(
        ctx: Context = CurrentContext(),
    ) -> str:
        """
        Clear all cached consensus results from session state.
        Returns the number of items cleared.
        """
        count = await clear_cache(ctx)
        return f"Cleared {count} cached consensus result(s) from session."

    @mcp.tool(
        annotations={
            "readOnlyHint": True,
            "openWorldHint": True,
        },
        tags=["consensus", "parallel", "ai", "elicitation"],
        # task=True disabled - Context (Session State) incompatible with background tasks
    )
    async def consensus_with_elicitation(
        prompt: Annotated[str, Field(description="The question to ask both AIs")],
        gemini_model: Annotated[
            str | None,
            Field(description="Optional Gemini model (e.g., gemini-2.0-flash)"),
        ] = None,
        ctx: Context = CurrentContext(),
    ) -> str:
        """
        Ask both Gemini and Codex in PARALLEL.
        If responses conflict, asks user which approach to prefer via elicitation.
        Returns the chosen response or synthesis based on user preference.
        """
        await safe_log(ctx, f"Starting consensus with elicitation: {prompt[:50]}...")
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

        # If one failed, return the successful one
        if not gemini_response.success and codex_response.success:
            await safe_log(ctx, "Gemini failed, returning Codex response")
            return f"**Codex Response (Gemini unavailable):**\n\n{codex_response.response}"

        if gemini_response.success and not codex_response.success:
            await safe_log(ctx, "Codex failed, returning Gemini response")
            return f"**Gemini Response (Codex unavailable):**\n\n{gemini_response.response}"

        if not gemini_response.success and not codex_response.success:
            return f"Both AIs failed:\n- Gemini: {gemini_response.error}\n- Codex: {codex_response.error}"

        await safe_progress(ctx, 60)

        # Check for conflict using simple heuristic
        # (responses differ significantly in length or content)
        gemini_words = set(gemini_response.response.lower().split())
        codex_words = set(codex_response.response.lower().split())
        common_words = gemini_words & codex_words
        all_words = gemini_words | codex_words

        # If less than 30% overlap, consider it a conflict
        overlap_ratio = len(common_words) / len(all_words) if all_words else 1.0
        has_conflict = overlap_ratio < 0.3

        await safe_log(ctx, f"Response overlap: {overlap_ratio:.1%}, conflict: {has_conflict}")

        if has_conflict:
            await safe_progress(ctx, 70)
            await safe_log(ctx, "Conflict detected, asking user preference...")

            # Try to elicit user preference
            try:
                elicit_result = await ctx.elicit(
                    message=(
                        f"AI yanıtları arasında önemli farklılık tespit edildi.\n\n"
                        f"**Soru:** {prompt[:100]}...\n\n"
                        f"**Gemini özet:** {gemini_response.response[:200]}...\n\n"
                        f"**Codex özet:** {codex_response.response[:200]}...\n\n"
                        f"Hangisini tercih edersiniz?"
                    ),
                    schema={
                        "type": "object",
                        "properties": {
                            "preference": {
                                "type": "string",
                                "enum": ["gemini", "codex", "synthesis"],
                                "description": "Tercih edilen yaklaşım"
                            }
                        },
                        "required": ["preference"]
                    }
                )

                await safe_progress(ctx, 80)

                if elicit_result.action == "accept" and elicit_result.data:
                    preference = elicit_result.data.get("preference", "synthesis")

                    if preference == "gemini":
                        await safe_log(ctx, "User chose Gemini")
                        return f"**Gemini Response (User Choice):**\n\n{gemini_response.response}"

                    if preference == "codex":
                        await safe_log(ctx, "User chose Codex")
                        return f"**Codex Response (User Choice):**\n\n{codex_response.response}"

                # Default to synthesis
                await safe_log(ctx, "User chose synthesis or declined")

            except Exception as e:
                await safe_log(ctx, f"Elicitation not available: {e}, falling back to synthesis")

        # Synthesize responses
        await safe_progress(ctx, 85)
        await safe_log(ctx, "Synthesizing responses...")

        synthesis_prompt = f"""İki farklı AI'dan aynı soru için yanıtlar aldım. Lütfen bunları karşılaştır ve sentezle:

SORU: {prompt}

GEMINI YANITI:
{gemini_response.response}

CODEX YANITI:
{codex_response.response}

Lütfen:
1. Ortak noktaları belirt
2. Farklılıkları belirt
3. En iyi yaklaşımı öner"""

        synthesis_response = await call_gemini(synthesis_prompt, gemini_model, ctx)

        # Create and cache result
        result = SynthesisResult(
            gemini=gemini_response,
            codex=codex_response,
            synthesis=synthesis_response,
        )
        await cache_consensus_result(ctx, prompt, result)

        await safe_progress(ctx, 100)
        await safe_log(ctx, "Consensus with elicitation completed")

        return result.format_markdown()
