from __future__ import annotations

import re
import socket
from typing import Dict, Any, Optional, List

import idna

from .config import (
    IANA_WHOIS_HOST,
    WhoisDefaults,
    TldConfig,
)


def to_ascii_domain(domain: str) -> str:
    labels = domain.strip().lower().split(".")
    return ".".join(idna.encode(lbl).decode("ascii") for lbl in labels if lbl)


def _whois_query(server: str, query: str, timeout_seconds: int) -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout_seconds)
    s.connect((server, 43))
    s.sendall(query.encode("utf-8", errors="ignore"))
    buf = b""
    while True:
        chunk = s.recv(4096)
        if not chunk:
            break
        buf += chunk
    s.close()
    return buf.decode("utf-8", errors="ignore")


def _parse_referral(text: str) -> Optional[str]:
    m = re.search(r"(?im)^\s*(refer|whois|whois server)\s*:\s*([A-Za-z0-9.\-]+)\s*$", text)
    return m.group(2).strip().lower() if m else None


def _match_not_found(text: str, patterns: List[str]) -> bool:
    t = text.lower()
    return any(pat.lower() in t for pat in patterns)


def _extract_expiry(text: str, patterns: List[str]) -> Optional[str]:
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def query_whois(
    domain: str,
    defaults: WhoisDefaults,
    tld_config: Optional[TldConfig],
) -> Dict[str, Any]:
    """
    Query WHOIS for a domain using config:
      - if TLD server configured, query it
      - else ask IANA WHOIS once to find a referral
      - optionally follow a referral in the result
    Returns dict: method, available, expiration_date, error
    """
    ascii_domain = to_ascii_domain(domain)
    tld = ascii_domain.rsplit(".", 1)[-1].lower()

    server = tld_config.server if tld_config else None
    query_template = tld_config.query_format if tld_config else "{domain}\r\n"
    not_found_patterns = (
        tld_config.not_found_patterns if tld_config and tld_config.not_found_patterns
        else defaults.generic_not_found_patterns
    )
    expiry_patterns = (
        tld_config.expiry_patterns if tld_config and tld_config.expiry_patterns
        else defaults.generic_expiry_patterns
    )

    def run(host: str) -> str:
        query = query_template.format(domain=ascii_domain)
        return _whois_query(host, query, defaults.timeout_seconds)

    # Discover server via IANA if none configured
    if not server:
        try:
            iana_text = run(IANA_WHOIS_HOST)
            referred = _parse_referral(iana_text)
            if not referred:
                return {
                    "method": "WHOIS",
                    "available": None,
                    "expiration_date": None,
                    "error": f"No WHOIS server configured or referred for .{tld}",
                }
            server = referred
        except Exception as exc:
            return {"method": "WHOIS", "available": None, "expiration_date": None, "error": f"IANA WHOIS failed: {exc}"}

    try:
        text = run(server)

        # Follow referral if configured and result is not "not found"
        if defaults.follow_referral and not _match_not_found(text, not_found_patterns):
            referred = _parse_referral(text)
            if referred and referred != server:
                try:
                    second = run(referred)
                    if len(second) > len(text):
                        text = second
                except Exception:
                    pass

        if _match_not_found(text, not_found_patterns):
            return {"method": "WHOIS", "available": True, "expiration_date": None}

        expiration = _extract_expiry(text, expiry_patterns)
        return {"method": "WHOIS", "available": False, "expiration_date": expiration}

    except Exception as exc:
        return {"method": "WHOIS", "available": None, "expiration_date": None, "error": str(exc)}
