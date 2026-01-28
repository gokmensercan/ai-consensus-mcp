"""Session State utilities for caching AI responses

Hybrid approach: Uses file-based cache for persistence across MCP sessions,
and optionally MCP session state when available.
"""

import hashlib
import json
from pathlib import Path
from typing import Optional

from fastmcp import Context
from models import ConsensusResult, SynthesisResult


# File-based cache directory
CACHE_DIR = Path.home() / ".cache" / "ai-consensus-mcp"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_cache_key(prompt: str) -> str:
    """Generate a cache key from prompt"""
    return f"consensus_{hashlib.md5(prompt.encode()).hexdigest()[:12]}"


def _get_cache_file(key: str) -> Path:
    """Get the cache file path for a key"""
    return CACHE_DIR / f"{key}.json"


def _get_history_file() -> Path:
    """Get the history file path"""
    return CACHE_DIR / "history.json"


async def cache_consensus_result(
    ctx: Optional[Context], prompt: str, result: ConsensusResult | SynthesisResult
) -> None:
    """Cache consensus result in file-based cache and optionally session state"""
    key = get_cache_key(prompt)
    data = result.model_dump()

    # File-based cache (always works)
    cache_file = _get_cache_file(key)
    cache_file.write_text(json.dumps(data, default=str))

    # Update history
    history_file = _get_history_file()
    history = []
    if history_file.exists():
        try:
            history = json.loads(history_file.read_text())
        except json.JSONDecodeError:
            history = []

    history.append({
        "prompt": prompt,
        "key": key,
        "timestamp": result.timestamp,
        "type": "synthesis" if isinstance(result, SynthesisResult) else "consensus"
    })
    # Keep last 10 queries
    history_file.write_text(json.dumps(history[-10:], default=str))

    # Also try MCP session state if context available
    if ctx:
        try:
            await ctx.set_state(key, data)
            await ctx.set_state("consensus_history", history[-10:])
        except Exception:
            pass  # Session state not available, that's OK


async def get_cached_result(
    ctx: Optional[Context], prompt: str
) -> ConsensusResult | SynthesisResult | None:
    """Get cached result from file cache or session state"""
    key = get_cache_key(prompt)
    data = None

    # Try MCP session state first (faster if available)
    if ctx:
        try:
            data = await ctx.get_state(key)
        except Exception:
            pass

    # Fall back to file cache
    if data is None:
        cache_file = _get_cache_file(key)
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text())
            except (json.JSONDecodeError, IOError):
                data = None

    if data is None:
        return None

    # Determine type and reconstruct
    if "synthesis" in data:
        return SynthesisResult.model_validate(data)
    return ConsensusResult.model_validate(data)


async def get_last_result(ctx: Optional[Context]) -> dict | None:
    """Get the last consensus result from cache"""
    history = None

    # Try MCP session state first
    if ctx:
        try:
            history = await ctx.get_state("consensus_history")
        except Exception:
            pass

    # Fall back to file cache
    if not history:
        history_file = _get_history_file()
        if history_file.exists():
            try:
                history = json.loads(history_file.read_text())
            except (json.JSONDecodeError, IOError):
                history = None

    if not history:
        return None

    last = history[-1]
    key = last["key"]
    data = None

    # Try MCP session state first
    if ctx:
        try:
            data = await ctx.get_state(key)
        except Exception:
            pass

    # Fall back to file cache
    if data is None:
        cache_file = _get_cache_file(key)
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text())
            except (json.JSONDecodeError, IOError):
                data = None

    if data:
        return {"prompt": last["prompt"], "type": last["type"], "data": data}
    return None


async def clear_cache(ctx: Optional[Context]) -> int:
    """Clear all cached consensus results. Returns number of items cleared."""
    count = 0
    history = []

    # Get history from file cache
    history_file = _get_history_file()
    if history_file.exists():
        try:
            history = json.loads(history_file.read_text())
            count = len(history)
        except (json.JSONDecodeError, IOError):
            pass

    # Delete all cached files
    for item in history:
        cache_file = _get_cache_file(item["key"])
        if cache_file.exists():
            cache_file.unlink()

        # Also try to clear from MCP session state
        if ctx:
            try:
                await ctx.delete_state(item["key"])
            except Exception:
                pass

    # Clear history file
    if history_file.exists():
        history_file.unlink()

    # Clear MCP session state history
    if ctx:
        try:
            await ctx.delete_state("consensus_history")
        except Exception:
            pass

    return count
