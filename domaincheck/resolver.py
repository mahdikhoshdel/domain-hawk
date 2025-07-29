from __future__ import annotations

from typing import Dict, Any

from .rdap_client import query_rdap
from .whois_client import query_whois
from .config import load_whois_config


# Load WHOIS configuration once at import
_WHOIS_DEFAULTS, _TLD_MAP = load_whois_config()


def resolve_domain(domain: str) -> Dict[str, Any]:
    """
    RDAP-first; if no RDAP server for the TLD, fallback to WHOIS configured by YAML.
    """
    rdap = query_rdap(domain)
    if rdap.get("available") is None and "No RDAP server" in (rdap.get("error") or ""):
        tld = domain.rsplit(".", 1)[-1].lower()
        tcfg = _TLD_MAP.get(tld)
        return query_whois(domain, _WHOIS_DEFAULTS, tcfg)
    return rdap
