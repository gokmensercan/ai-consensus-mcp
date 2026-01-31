"""Common subprocess runner with retry, timeout, and exit code handling"""

import asyncio
import logging

from fastmcp import Context
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
)

from config import settings
from models import AIResponse
from utils import safe_log

logger = logging.getLogger(__name__)


class SubprocessError(Exception):
    """Transient subprocess error — eligible for retry."""

    pass


class SubprocessFatalError(Exception):
    """Permanent subprocess error — no retry."""

    pass


async def _run_once(
    cmd: list[str],
    provider: str,
    ctx: Context | None,
    timeout: int | None,
) -> AIResponse:
    """Execute a CLI command once and return an AIResponse."""
    if timeout is None:
        timeout = settings.PROVIDER_TIMEOUT_SECONDS

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError as e:
        raise SubprocessFatalError(
            f"{provider} command not found: {e}"
        ) from e

    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise SubprocessError(
            f"{provider} CLI timed out after {timeout}s"
        )

    if proc.returncode != 0:
        error_msg = stderr.decode("utf-8").strip() if stderr else f"exit code {proc.returncode}"
        raise SubprocessError(
            f"{provider} CLI failed (rc={proc.returncode}): {error_msg}"
        )

    output = stdout.decode("utf-8").strip()

    if not output and stderr:
        error_msg = stderr.decode("utf-8").strip()
        return AIResponse(
            provider=provider, response="", success=False, error=error_msg
        )

    return AIResponse(provider=provider, response=output or "(empty)", success=True)


async def run_cli_subprocess(
    cmd: list[str],
    provider: str,
    ctx: Context | None = None,
    timeout: int | None = None,
) -> AIResponse:
    """
    Run a CLI subprocess with retry, timeout, and exit code handling.

    - Retries transient errors (SubprocessError) with exponential backoff + jitter
    - Does NOT retry fatal errors (SubprocessFatalError, e.g. command not found)
    - Enforces a timeout on proc.communicate()
    - Checks exit code and treats non-zero as transient error
    """
    await safe_log(ctx, f"Calling {provider} CLI...")

    max_retries = settings.PROVIDER_MAX_RETRIES
    base_delay = settings.PROVIDER_RETRY_BASE_DELAY

    @retry(
        retry=retry_if_exception_type(SubprocessError),
        stop=stop_after_attempt(max_retries),
        wait=wait_exponential_jitter(initial=base_delay, max=30),
        reraise=True,
    )
    async def _attempt() -> AIResponse:
        return await _run_once(cmd, provider, ctx, timeout)

    try:
        return await _attempt()
    except SubprocessFatalError as e:
        logger.warning("%s fatal error: %s", provider, e)
        return AIResponse(
            provider=provider, response="", success=False, error=str(e)
        )
    except SubprocessError as e:
        logger.warning(
            "%s failed after %d retries: %s", provider, max_retries, e
        )
        return AIResponse(
            provider=provider, response="", success=False, error=str(e)
        )
    except Exception as e:
        logger.exception("Unexpected error calling %s", provider)
        return AIResponse(
            provider=provider, response="", success=False, error=str(e)
        )
