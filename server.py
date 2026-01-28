#!/usr/bin/env python3
"""
AI Consensus MCP Server - Gemini + Codex parallel execution
"""

import asyncio
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ai-consensus")


async def call_gemini(prompt: str, model: str = None) -> str:
    """Call Gemini CLI"""
    cmd = ["gemini", "-p", prompt, "-o", "text"]
    if model:
        cmd.extend(["-m", model])

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd="/tmp"
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        output = stdout.decode("utf-8").strip()
        if not output and stderr:
            output = f"Error: {stderr.decode('utf-8').strip()}"
        return output or "(empty)"
    except asyncio.TimeoutError:
        return "Error: Timeout (120s)"
    except Exception as e:
        return f"Error: {e}"


async def call_codex(prompt: str) -> str:
    """Call Codex CLI"""
    cmd = ["codex", "exec", prompt]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd="/tmp"
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        output = stdout.decode("utf-8").strip()
        if not output and stderr:
            output = f"Error: {stderr.decode('utf-8').strip()}"
        return output or "(empty)"
    except asyncio.TimeoutError:
        return "Error: Timeout (120s)"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
async def ask_gemini(prompt: str, model: str = None) -> str:
    """
    Ask Gemini AI a question using local Gemini CLI.

    Args:
        prompt: The prompt to send to Gemini
        model: Optional model (e.g., gemini-2.0-flash)
    """
    return await call_gemini(prompt, model)


@mcp.tool()
async def ask_codex(prompt: str) -> str:
    """
    Ask Codex AI a question using local Codex CLI.

    Args:
        prompt: The prompt to send to Codex
    """
    return await call_codex(prompt)


@mcp.tool()
async def consensus(prompt: str, gemini_model: str = None) -> str:
    """
    Ask both Gemini and Codex the same question in PARALLEL and return both responses.
    Use this for getting multiple AI perspectives on a problem.

    Args:
        prompt: The prompt to send to both AIs
        gemini_model: Optional Gemini model
    """
    # Run both in parallel
    gemini_task = asyncio.create_task(call_gemini(prompt, gemini_model))
    codex_task = asyncio.create_task(call_codex(prompt))

    # Wait for both
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
    Ask both Gemini and Codex, then ask Gemini to synthesize/compare the responses.
    Returns individual responses plus a synthesis.

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


if __name__ == "__main__":
    mcp.run(transport="stdio")
