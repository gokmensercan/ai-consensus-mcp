"""Context helper functions for MCP tools.

Provides centralized logging and progress reporting utilities
that safely handle Context availability.
"""

from fastmcp import Context


async def safe_log(ctx: Context | None, message: str) -> None:
    """
    Safely log a message if context is available.

    Args:
        ctx: MCP Context (may be None outside request scope)
        message: Log message to send
    """
    if ctx is not None:
        try:
            await ctx.info(message)
        except (ValueError, AttributeError, RuntimeError):
            pass  # Context not available outside request


async def safe_progress(ctx: Context | None, progress: int, total: int = 100) -> None:
    """
    Safely report progress if context is available.

    Args:
        ctx: MCP Context (may be None outside request scope)
        progress: Current progress value
        total: Total progress value (default 100)
    """
    if ctx is not None:
        try:
            await ctx.report_progress(progress=progress, total=total)
        except (ValueError, AttributeError, RuntimeError):
            pass  # Context not available outside request
