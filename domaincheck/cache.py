from __future__ import annotations

import json
import os
import tempfile
from typing import Dict, Any

from .time_utils import parse_iso, now_utc
from .config import DEFAULT_TTL_DAYS, NEAR_EXPIRY_DAYS, NEAR_EXPIRY_TTL_DAYS


def load_cache(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache_atomic(cache: Dict[str, Any], path: str) -> None:
    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".cache.", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass


def is_stale(entry: Dict[str, Any], ttl_days: int = DEFAULT_TTL_DAYS) -> bool:
    """
    Staleness rules:
      - Missing/invalid checked_at
      - Age > ttl_days
      - If near expiry (< NEAR_EXPIRY_DAYS), refresh daily (NEAR_EXPIRY_TTL_DAYS)
    """
    now = now_utc()
    checked_at = parse_iso(entry.get("checked_at"))
    if not checked_at:
        return True

    age_days = (now - checked_at).total_seconds() / 86400.0
    if age_days > ttl_days:
        return True

    exp_raw = entry.get("expiration_date")
    exp_dt = parse_iso(exp_raw) if exp_raw else None
    if exp_dt:
        days_left = (exp_dt - now).total_seconds() / 86400.0
        if days_left <= NEAR_EXPIRY_DAYS and age_days > NEAR_EXPIRY_TTL_DAYS:
            return True

    return False
