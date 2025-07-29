from __future__ import annotations

import datetime as dt
from typing import Optional


UTC = dt.timezone.utc


def now_utc() -> dt.datetime:
    """Return aware UTC datetime."""
    return dt.datetime.now(UTC)


def now_iso() -> str:
    """Return ISO-8601 in UTC with trailing 'Z'."""
    return now_utc().replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso(value: str | None) -> Optional[dt.datetime]:
    """
    Parse ISO string to aware UTC datetime.
    Accepts '...Z' or timezone offset; naive is assumed UTC.
    """
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt_obj = dt.datetime.fromisoformat(text)
        if dt_obj.tzinfo is None:
            dt_obj = dt_obj.replace(tzinfo=UTC)
        return dt_obj.astimezone(UTC)
    except Exception:
        return None


def normalize_iso_utc(value: str | None) -> str | None:
    """
    Normalize any parseable timestamp into ISO-8601 UTC with 'Z'.
    Returns original string if parsing fails or value is None.
    """
    if not value:
        return None
    parsed = parse_iso(value)
    return parsed.isoformat().replace("+00:00", "Z") if parsed else value
