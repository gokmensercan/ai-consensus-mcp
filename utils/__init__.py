"""Utility functions for AI Consensus MCP Server"""

from utils.context_helpers import safe_log, safe_progress
from utils.state import (
    cache_consensus_result,
    get_cached_result,
    get_last_result,
    clear_cache,
    get_cache_key,
)

__all__ = [
    "safe_log",
    "safe_progress",
    "cache_consensus_result",
    "get_cached_result",
    "get_last_result",
    "clear_cache",
    "get_cache_key",
]
