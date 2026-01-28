"""Consensus tools - parallel AI queries"""

import asyncio
from providers import call_gemini, call_codex


def register_consensus_tools(mcp):
    """Register consensus tools to the MCP server"""

    @mcp.tool()
    async def consensus(prompt: str, gemini_model: str = None) -> str:
        """
        Ask both Gemini and Codex the same question in PARALLEL.
        Returns both responses for comparison.

        Args:
            prompt: The prompt to send to both AIs
            gemini_model: Optional Gemini model
        """
        # Run both in parallel
        gemini_task = asyncio.create_task(call_gemini(prompt, gemini_model))
        codex_task = asyncio.create_task(call_codex(prompt))

        gemini_response, codex_response = await asyncio.gather(
            gemini_task, codex_task, return_exceptions=True
        )

        # Handle exceptions
        if isinstance(gemini_response, Exception):
            gemini_response = f"Error: {gemini_response}"
        if isinstance(codex_response, Exception):
            codex_response = f"Error: {codex_response}"

        return f"""## Gemini Response:
{gemini_response}

---

## Codex Response:
{codex_response}"""

    @mcp.tool()
    async def consensus_with_synthesis(prompt: str, gemini_model: str = None) -> str:
        """
        Ask both Gemini and Codex in PARALLEL, then synthesize responses.
        Returns individual responses plus a combined synthesis.

        Args:
            prompt: The prompt to send to both AIs
            gemini_model: Optional Gemini model
        """
        # Get parallel responses
        gemini_task = asyncio.create_task(call_gemini(prompt, gemini_model))
        codex_task = asyncio.create_task(call_codex(prompt))

        gemini_response, codex_response = await asyncio.gather(
            gemini_task, codex_task, return_exceptions=True
        )

        if isinstance(gemini_response, Exception):
            gemini_response = f"Error: {gemini_response}"
        if isinstance(codex_response, Exception):
            codex_response = f"Error: {codex_response}"

        # Ask Gemini to synthesize
        synthesis_prompt = f"""İki farklı AI'dan aynı soru için yanıtlar aldım. Lütfen bunları karşılaştır ve sentezle:

SORU: {prompt}

GEMINI YANITI:
{gemini_response}

CODEX YANITI:
{codex_response}

Lütfen:
1. Ortak noktaları belirt
2. Farklılıkları belirt
3. En iyi yaklaşımı öner"""

        synthesis = await call_gemini(synthesis_prompt, gemini_model)

        return f"""## Gemini Response:
{gemini_response}

---

## Codex Response:
{codex_response}

---

## Synthesis (by Gemini):
{synthesis}"""
