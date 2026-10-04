"""
Result and analytical query cache service.
Prevents redundant computations, duplicate tool runs, and repeated LLM calls.
"""

from __future__ import annotations
import hashlib
import json
import time
from typing import Any, Optional, Dict
from app.utils.logging import logger

_ANALYTICS_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour


def _make_key(func_name: str, kwargs: dict) -> str:
    """Generate deterministic hash key for function name and arguments."""
    serialized = json.dumps(kwargs, sort_keys=True, default=str)
    return hashlib.sha256(f"{func_name}:{serialized}".encode("utf-8")).hexdigest()


def get_cached_result(func_name: str, kwargs: dict) -> Optional[Any]:
    """Retrieve result from cache if still valid."""
    key = _make_key(func_name, kwargs)
    entry = _ANALYTICS_CACHE.get(key)
    if entry:
        if time.time() - entry["timestamp"] < CACHE_TTL_SECONDS:
            logger.debug("Cache HIT for %s", func_name)
            return entry["data"]
        else:
            del _ANALYTICS_CACHE[key]
    return None


def set_cached_result(func_name: str, kwargs: dict, data: Any):
    """Store result in cache."""
    key = _make_key(func_name, kwargs)
    _ANALYTICS_CACHE[key] = {
        "timestamp": time.time(),
        "data": data,
    }


def clear_cache():
    """Clear analytical cache."""
    _ANALYTICS_CACHE.clear()
    logger.info("Cleared analytics cache.")
