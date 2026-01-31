"""Council tool - 3-stage LLM Council pipeline inspired by karpathy/llm-council"""

import asyncio
from typing import Annotated

from fastmcp import Context
from fastmcp.server.dependencies import CurrentContext
from pydantic import Field

from providers import call_gemini, call_codex, call_copilot
from models import AIResponse, CouncilResult
from models.council import PeerReview
from utils import (
    safe_log,
    safe_progress,
    cache_consensus_result,
    get_cached_result,
)


def _build_review_prompt(question: str, response_text: str) -> str:
    """Build an anonymized peer review prompt for a single response (Turkish)."""
    return f"""Bir AI modeli aşağıdaki soruya yanıt verdi. Lütfen bu yanıtı değerlendir.

SORU: {question}

YANIT:
{response_text}

Lütfen şu açılardan değerlendir:
1. Doğruluk: Yanıt faktüel olarak doğru mu?
2. Tamlık: Sorunun tüm yönleri ele alınmış mı?
3. Netlik: Yanıt açık ve anlaşılır mı?
4. Güçlü yönler: Yanıtın en iyi tarafları nelerdir?
5. Zayıf yönler: Hangi eksiklikler veya hatalar var?
6. Genel değerlendirme: 1-10 arası puan ver ve gerekçendir."""


def _build_review_prompt_multi(
    question: str, response_a_text: str, response_b_text: str
) -> str:
    """Build a peer review prompt for two responses (3-member council)."""
    return f"""İki farklı AI modeli aşağıdaki soruya yanıt verdi. Lütfen her iki yanıtı da değerlendir.

SORU: {question}

YANIT A:
{response_a_text}

YANIT B:
{response_b_text}

Lütfen her iki yanıt için şu açılardan değerlendir:
1. Doğruluk: Yanıtlar faktüel olarak doğru mu?
2. Tamlık: Sorunun tüm yönleri ele alınmış mı?
3. Netlik: Yanıtlar açık ve anlaşılır mı?
4. Güçlü yönler: Her yanıtın en iyi tarafları nelerdir?
5. Zayıf yönler: Hangi eksiklikler veya hatalar var?
6. Karşılaştırma: Hangi yanıt daha iyi ve neden?
7. Genel değerlendirme: Her yanıt için 1-10 arası puan ver ve gerekçendir."""


def _build_chairman_prompt(
    question: str,
    gemini_response: str,
    codex_response: str,
    gemini_review_text: str,
    codex_review_text: str,
) -> str:
    """Build the chairman synthesis prompt for 2-member council (Turkish)."""
    return f"""Sen bir LLM konseyinin başkanısın. İki farklı AI modelinden yanıtlar ve bunların karşılıklı değerlendirmeleri aşağıda verilmiştir. Tüm bilgileri sentezleyerek nihai ve kapsamlı bir yanıt üret.

SORU: {question}

--- MODEL A YANITI ---
{gemini_response}

--- MODEL B YANITI ---
{codex_response}

--- MODEL A'NIN, MODEL B YANITINA DEĞERLENDİRMESİ ---
{gemini_review_text}

--- MODEL B'NIN, MODEL A YANITINA DEĞERLENDİRMESİ ---
{codex_review_text}

Lütfen:
1. Her iki yanıtın güçlü yönlerini birleştir
2. Değerlendirmelerde belirtilen zayıf yönleri gider
3. Tutarsızlıkları çöz
4. Kapsamlı, doğru ve dengeli bir nihai sentez üret"""


def _build_chairman_prompt_3way(
    question: str,
    gemini_response: str,
    codex_response: str,
    copilot_response: str,
    gemini_review_text: str,
    codex_review_text: str,
    copilot_review_text: str,
) -> str:
    """Build the chairman synthesis prompt for 3-member council (Turkish)."""
    return f"""Sen bir LLM konseyinin başkanısın. Üç farklı AI modelinden yanıtlar ve bunların karşılıklı değerlendirmeleri aşağıda verilmiştir. Tüm bilgileri sentezleyerek nihai ve kapsamlı bir yanıt üret.

SORU: {question}

--- MODEL A YANITI ---
{gemini_response}

--- MODEL B YANITI ---
{codex_response}

--- MODEL C YANITI ---
{copilot_response}

--- MODEL A'NIN DEĞERLENDİRMESİ (Model B ve C hakkında) ---
{gemini_review_text}

--- MODEL B'NIN DEĞERLENDİRMESİ (Model A ve C hakkında) ---
{codex_review_text}

--- MODEL C'NIN DEĞERLENDİRMESİ (Model A ve B hakkında) ---
{copilot_review_text}

Lütfen:
1. Üç yanıtın güçlü yönlerini birleştir
2. Değerlendirmelerde belirtilen zayıf yönleri gider
3. Tutarsızlıkları çöz
4. Kapsamlı, doğru ve dengeli bir nihai sentez üret"""


def _make_review(reviewer: str, raw) -> PeerReview:
    """Convert a raw response or exception into a PeerReview."""
    if isinstance(raw, Exception):
        return PeerReview(
            reviewer=reviewer,
            review="",
            success=False,
            error=str(raw),
        )
    elif isinstance(raw, AIResponse):
        return PeerReview(
            reviewer=reviewer,
            review=raw.response if raw.success else "",
            success=raw.success,
            error=raw.error,
        )
    else:
        return PeerReview(
            reviewer=reviewer,
            review="",
            success=False,
            error="Unexpected response type",
        )


def register_council_tools(mcp):
    """Register council tools to the MCP server"""

    @mcp.tool(
        annotations={
            "readOnlyHint": True,
            "openWorldHint": True,
        },
        tags=["council", "parallel", "ai", "pipeline"],
    )
    async def council(
        prompt: Annotated[str, Field(description="The question to ask the council")],
        gemini_model: Annotated[
            str | None,
            Field(description="Optional Gemini model (e.g., gemini-2.0-flash)"),
        ] = None,
        chairman: Annotated[
            str,
            Field(description="Chairman model for final synthesis (gemini, codex, or copilot)"),
        ] = "gemini",
        use_cache: Annotated[
            bool,
            Field(description="Use cached result if available (default: True)"),
        ] = True,
        ctx: Context = CurrentContext(),
    ) -> str:
        """
        3-stage LLM Council pipeline inspired by karpathy/llm-council.

        Stage 1: Gemini, Codex, and Copilot answer the question in parallel.
        Stage 2: Each model reviews the other models' responses (peer review) in parallel.
        Stage 3: The chairman model synthesizes all responses and reviews into a final answer.
        """
        await safe_log(ctx, f"Starting council pipeline: {prompt[:50]}...")
        await safe_progress(ctx, 0)

        # Validate chairman
        if chairman not in ("gemini", "codex", "copilot"):
            return "Error: chairman must be 'gemini', 'codex', or 'copilot'"

        # Check cache first
        if use_cache:
            cached = await get_cached_result(ctx, prompt, model=gemini_model)
            if cached and isinstance(cached, CouncilResult):
                await safe_log(ctx, "Returning cached council result")
                await safe_progress(ctx, 100)
                return f"[CACHED]\n\n{cached.format_markdown()}"

        # ── Stage 1: First Opinions (parallel) ──
        await safe_log(ctx, "Stage 1: Getting initial opinions...")
        await safe_progress(ctx, 5)

        gemini_task = asyncio.create_task(call_gemini(prompt, gemini_model, ctx))
        codex_task = asyncio.create_task(call_codex(prompt, ctx))
        copilot_task = asyncio.create_task(call_copilot(prompt, ctx))

        gemini_response, codex_response, copilot_response = await asyncio.gather(
            gemini_task, codex_task, copilot_task, return_exceptions=True
        )

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

        await safe_progress(ctx, 25)
        await safe_log(ctx, "Stage 1 complete.")

        # Helper to get response text
        def _resp_text(resp: AIResponse) -> str:
            return resp.response if resp.success else f"Error: {resp.error}"

        gemini_text = _resp_text(gemini_response)
        codex_text = _resp_text(codex_response)
        copilot_text = _resp_text(copilot_response)

        # ── Stage 2: Peer Reviews (parallel) ──
        await safe_log(ctx, "Stage 2: Peer reviews...")

        # Each model reviews the other two
        gemini_review_prompt = _build_review_prompt_multi(
            prompt, codex_text, copilot_text
        )
        codex_review_prompt = _build_review_prompt_multi(
            prompt, gemini_text, copilot_text
        )
        copilot_review_prompt = _build_review_prompt_multi(
            prompt, gemini_text, codex_text
        )

        gemini_review_task = asyncio.create_task(
            call_gemini(gemini_review_prompt, gemini_model, ctx)
        )
        codex_review_task = asyncio.create_task(
            call_codex(codex_review_prompt, ctx)
        )
        copilot_review_task = asyncio.create_task(
            call_copilot(copilot_review_prompt, ctx)
        )

        gemini_review_raw, codex_review_raw, copilot_review_raw = await asyncio.gather(
            gemini_review_task, codex_review_task, copilot_review_task,
            return_exceptions=True,
        )

        gemini_review = _make_review("gemini", gemini_review_raw)
        codex_review = _make_review("codex", codex_review_raw)
        copilot_review = _make_review("copilot", copilot_review_raw)

        await safe_progress(ctx, 55)
        await safe_log(ctx, "Stage 2 complete.")

        # ── Stage 3: Chairman Synthesis ──
        await safe_log(ctx, f"Stage 3: Chairman synthesis (by {chairman})...")

        gemini_review_text = gemini_review.review if gemini_review.success else f"Error: {gemini_review.error}"
        codex_review_text = codex_review.review if codex_review.success else f"Error: {codex_review.error}"
        copilot_review_text = copilot_review.review if copilot_review.success else f"Error: {copilot_review.error}"

        chairman_prompt = _build_chairman_prompt_3way(
            question=prompt,
            gemini_response=gemini_text,
            codex_response=codex_text,
            copilot_response=copilot_text,
            gemini_review_text=gemini_review_text,
            codex_review_text=codex_review_text,
            copilot_review_text=copilot_review_text,
        )

        if chairman == "gemini":
            synthesis_response = await call_gemini(chairman_prompt, gemini_model, ctx)
        elif chairman == "codex":
            synthesis_response = await call_codex(chairman_prompt, ctx)
        else:
            synthesis_response = await call_copilot(chairman_prompt, ctx)

        if isinstance(synthesis_response, Exception):
            synthesis_response = AIResponse(
                provider=chairman,
                response="",
                success=False,
                error=str(synthesis_response),
            )

        await safe_progress(ctx, 90)
        await safe_log(ctx, "Stage 3 complete.")

        # ── Build result and cache ──
        result = CouncilResult(
            gemini=gemini_response,
            codex=codex_response,
            copilot=copilot_response,
            gemini_review=gemini_review,
            codex_review=codex_review,
            copilot_review=copilot_review,
            chairman=chairman,
            chairman_synthesis=synthesis_response,
        )

        await cache_consensus_result(ctx, prompt, result, model=gemini_model)

        await safe_progress(ctx, 100)
        await safe_log(ctx, "Council pipeline completed and cached.")

        return result.format_markdown()
