from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Literal


Method = Literal["RDAP", "WHOIS", "unknown"]
Source = Literal["cache", "network"]


@dataclass(frozen=True)
class DomainResult:
    """
    Normalized result of a domain query.
    """
    domain: str
    available: Optional[bool]           # True = free, False = taken, None = error/unknown
    expiration_date: Optional[str]      # ISO-8601 UTC with 'Z' when available; else registry raw or None
    checked_at: str                     # ISO-8601 UTC with 'Z'
    method: Method                      # RDAP or WHOIS
    source: Source                      # cache or network
    error: Optional[str] = None         # error message when available is None
