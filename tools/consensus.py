"""Consensus tools - parallel AI queries with progress reporting and caching"""

import asyncio
from typing import Annotated

from fastmcp import Context
from fastmcp.server.dependencies import CurrentContext
from pydantic import Field

from providers import call_gemini, call_codex, call_copilot
from models import AIResponse, ConsensusResult, SynthesisResult, CouncilResult
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
        Ask Gemini, Codex, and Copilot the same question in PARALLEL.
        Returns all responses for comparison with structured output.
        Results are cached in session state for quick retrieval.
        """
        await safe_log(ctx, f"Starting consensus query: {prompt[:50]}...")
        await safe_progress(ctx, 0)

        # Check cache first
        if use_cache:
            cached = await get_cached_result(ctx, prompt, model=gemini_model)
            if cached and isinstance(cached, ConsensusResult):
                await safe_log(ctx, "Returning cached result")
                await safe_progress(ctx, 100)
                return f"[CACHED]\n\n{cached.format_markdown()}"

        await safe_progress(ctx, 5)

        # Run all three in parallel
        gemini_task = asyncio.create_task(call_gemini(prompt, gemini_model, ctx))
        codex_task = asyncio.create_task(call_codex(prompt, ctx))
        copilot_task = asyncio.create_task(call_copilot(prompt, ctx))

        await safe_progress(ctx, 10)

        gemini_response, codex_response, copilot_response = await asyncio.gather(
            gemini_task, codex_task, copilot_task, return_exceptions=True
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
        if isinstance(copilot_response, Exception):
            copilot_response = AIResponse(
                provider="copilot",
                response="",
                success=False,
                error=str(copilot_response),
            )

        # Create structured result
        result = ConsensusResult(
            gemini=gemini_response,
            codex=codex_response,
            copilot=copilot_response,
        )

        # Cache the result
        await cache_consensus_result(ctx, prompt, result, model=gemini_model)

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
        Ask Gemini, Codex, and Copilot in PARALLEL, then synthesize responses.
        Returns individual responses plus a combined synthesis.
        Results are cached in session state for quick retrieval.
        """
        await safe_log(ctx, f"Starting consensus with synthesis: {prompt[:50]}...")
        await safe_progress(ctx, 0)

        # Check cache first
        if use_cache:
            cached = await get_cached_result(ctx, prompt, model=gemini_model)
            if cached and isinstance(cached, SynthesisResult):
                await safe_log(ctx, "Returning cached synthesis result")
                await safe_progress(ctx, 100)
                return f"[CACHED]\n\n{cached.format_markdown()}"

        await safe_progress(ctx, 5)

        # Get parallel responses
        gemini_task = asyncio.create_task(call_gemini(prompt, gemini_model, ctx))
        codex_task = asyncio.create_task(call_codex(prompt, ctx))
        copilot_task = asyncio.create_task(call_copilot(prompt, ctx))

        await safe_progress(ctx, 10)

        gemini_response, codex_response, copilot_response = await asyncio.gather(
            gemini_task, codex_task, copilot_task, return_exceptions=True
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
        if isinstance(copilot_response, Exception):
            copilot_response = AIResponse(
                provider="copilot",
                response="",
                success=False,
                error=str(copilot_response),
            )

        await safe_log(ctx, "Synthesizing responses...")
        await safe_progress(ctx, 60)

        # Ask Gemini to synthesize
        synthesis_prompt = f"""Üç farklı AI'dan aynı soru için yanıtlar aldım. Lütfen bunları karşılaştır ve sentezle:

SORU: {prompt}

GEMINI YANITI:
{gemini_response.response if gemini_response.success else f"Error: {gemini_response.error}"}

CODEX YANITI:
{codex_response.response if codex_response.success else f"Error: {codex_response.error}"}

COPILOT YANITI:
{copilot_response.response if copilot_response.success else f"Error: {copilot_response.error}"}

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
            copilot=copilot_response,
            synthesis=synthesis_response,
        )

        # Cache the result
        await cache_consensus_result(ctx, prompt, result, model=gemini_model)

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

        if result_type == "council":
            parsed = CouncilResult.model_validate(data)
        elif result_type == "synthesis":
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
        Ask Gemini, Codex, and Copilot in PARALLEL.
        If responses conflict, asks user which approach to prefer via elicitation.
        Returns the chosen response or synthesis based on user preference.
        """
        await safe_log(ctx, f"Starting consensus with elicitation: {prompt[:50]}...")
        await safe_progress(ctx, 0)

        # Get parallel responses
        gemini_task = asyncio.create_task(call_gemini(prompt, gemini_model, ctx))
        codex_task = asyncio.create_task(call_codex(prompt, ctx))
        copilot_task = asyncio.create_task(call_copilot(prompt, ctx))

        await safe_progress(ctx, 10)

        gemini_response, codex_response, copilot_response = await asyncio.gather(
            gemini_task, codex_task, copilot_task, return_exceptions=True
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
        if isinstance(copilot_response, Exception):
            copilot_response = AIResponse(
                provider="copilot",
                response="",
                success=False,
                error=str(copilot_response),
            )

        # Collect successful responses
        successful = []
        if gemini_response.success:
            successful.append(("gemini", gemini_response))
        if codex_response.success:
            successful.append(("codex", codex_response))
        if copilot_response.success:
            successful.append(("copilot", copilot_response))

        if len(successful) == 0:
            return (
                f"All AIs failed:\n"
                f"- Gemini: {gemini_response.error}\n"
                f"- Codex: {codex_response.error}\n"
                f"- Copilot: {copilot_response.error}"
            )

        if len(successful) == 1:
            name, resp = successful[0]
            failed_names = [n for n in ("gemini", "codex", "copilot") if n != name]
            return f"**{name.capitalize()} Response ({', '.join(failed_names)} unavailable):**\n\n{resp.response}"

        await safe_progress(ctx, 60)

        # Check for conflict using pairwise overlap
        def _word_set(text: str) -> set[str]:
            return set(text.lower().split())

        word_sets = {name: _word_set(resp.response) for name, resp in successful}
        names = list(word_sets.keys())
        overlap_ratios = []
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                common = word_sets[names[i]] & word_sets[names[j]]
                total = word_sets[names[i]] | word_sets[names[j]]
                ratio = len(common) / len(total) if total else 1.0
                overlap_ratios.append(ratio)

        min_overlap = min(overlap_ratios) if overlap_ratios else 1.0
        has_conflict = min_overlap < 0.3

        await safe_log(ctx, f"Min pairwise overlap: {min_overlap:.1%}, conflict: {has_conflict}")

        if has_conflict:
            await safe_progress(ctx, 70)
            await safe_log(ctx, "Conflict detected, asking user preference...")

            # Build summary for elicitation
            summaries = []
            for name, resp in successful:
                summaries.append(f"**{name.capitalize()} özet:** {resp.response[:200]}...")

            try:
                elicit_result = await ctx.elicit(
                    message=(
                        f"AI yanıtları arasında önemli farklılık tespit edildi.\n\n"
                        f"**Soru:** {prompt[:100]}...\n\n"
                        + "\n\n".join(summaries)
                        + "\n\nHangisini tercih edersiniz?"
                    ),
                    schema={
                        "type": "object",
                        "properties": {
                            "preference": {
                                "type": "string",
                                "enum": ["gemini", "codex", "copilot", "synthesis"],
                                "description": "Tercih edilen yaklaşım"
                            }
                        },
                        "required": ["preference"]
                    }
                )

                await safe_progress(ctx, 80)

                if elicit_result.action == "accept" and elicit_result.data:
                    preference = elicit_result.data.get("preference", "synthesis")

                    if preference == "gemini" and gemini_response.success:
                        await safe_log(ctx, "User chose Gemini")
                        return f"**Gemini Response (User Choice):**\n\n{gemini_response.response}"

                    if preference == "codex" and codex_response.success:
                        await safe_log(ctx, "User chose Codex")
                        return f"**Codex Response (User Choice):**\n\n{codex_response.response}"

                    if preference == "copilot" and copilot_response.success:
                        await safe_log(ctx, "User chose Copilot")
                        return f"**Copilot Response (User Choice):**\n\n{copilot_response.response}"

                # Default to synthesis
                await safe_log(ctx, "User chose synthesis or declined")

            except Exception as e:
                await safe_log(ctx, f"Elicitation not available: {e}, falling back to synthesis")

        # Synthesize responses
        await safe_progress(ctx, 85)
        await safe_log(ctx, "Synthesizing responses...")

        synthesis_prompt = f"""Üç farklı AI'dan aynı soru için yanıtlar aldım. Lütfen bunları karşılaştır ve sentezle:

SORU: {prompt}

GEMINI YANITI:
{gemini_response.response if gemini_response.success else f"Error: {gemini_response.error}"}

CODEX YANITI:
{codex_response.response if codex_response.success else f"Error: {codex_response.error}"}

COPILOT YANITI:
{copilot_response.response if copilot_response.success else f"Error: {copilot_response.error}"}

Lütfen:
1. Ortak noktaları belirt
2. Farklılıkları belirt
3. En iyi yaklaşımı öner"""

        synthesis_response = await call_gemini(synthesis_prompt, gemini_model, ctx)

        # Create and cache result
        result = SynthesisResult(
            gemini=gemini_response,
            codex=codex_response,
            copilot=copilot_response,
            synthesis=synthesis_response,
        )
        await cache_consensus_result(ctx, prompt, result, model=gemini_model)

        await safe_progress(ctx, 100)
        await safe_log(ctx, "Consensus with elicitation completed")

        return result.format_markdown()
