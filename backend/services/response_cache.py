"""In-memory TTL cache for repeated natural-language queries."""

from __future__ import annotations

import hashlib
import threading
import time
from typing import Any

from config import CACHE_TTL_SECONDS

_lock = threading.Lock()
_store: dict[str, tuple[float, Any]] = {}


def make_cache_key(query: str, intent: str, data_source: str) -> str:
    raw = f"{query.strip().lower()}|{intent}|{data_source}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def cache_get(key: str) -> Any | None:
    now = time.time()
    with _lock:
        entry = _store.get(key)
        if not entry:
            return None
        expires_at, value = entry
        if expires_at < now:
            _store.pop(key, None)
            return None
        return value


def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    ttl_seconds = CACHE_TTL_SECONDS if ttl is None else ttl
    with _lock:
        _store[key] = (time.time() + ttl_seconds, value)


def cache_clear() -> None:
    with _lock:
        _store.clear()


def cache_size() -> int:
    with _lock:
        return len(_store)
