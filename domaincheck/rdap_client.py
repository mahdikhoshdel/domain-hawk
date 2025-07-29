from __future__ import annotations

from typing import Optional, Dict, Any
import requests

from .config import REQUEST_TIMEOUT_SECONDS


def rdap_base_url_for_tld(tld: str) -> Optional[str]:
    """
    Discover RDAP base URL for a TLD using IANA bootstrap.
    """
    try:
        resp = requests.get("https://data.iana.org/rdap/dns.json", timeout=REQUEST_TIMEOUT_SECONDS)
        resp.raise_for_status()
        for service in resp.json().get("services", []):
            tlds, urls = service[0], service[1]
            if any(tld.lower() == t.strip(".").lower() for t in tlds):
                return urls[0]
    except Exception:
        return None
    return None


def query_rdap(domain: str) -> Dict[str, Any]:
    """
    Query RDAP for a domain. Returns a normalized dict:
      - method, available, expiration_date, error
    """
    tld = domain.rsplit(".", 1)[-1].lower()
    base = rdap_base_url_for_tld(tld)
    if not base:
        return {"method": "RDAP", "available": None, "expiration_date": None,
                "error": f"No RDAP server found for .{tld}"}

    try:
        r = requests.get(f"{base}/domain/{domain}", timeout=REQUEST_TIMEOUT_SECONDS)
        if r.status_code == 404:
            return {"method": "RDAP", "available": True, "expiration_date": None}
        r.raise_for_status()
        data = r.json()

        expiration = None
        for event in data.get("events", []):
            if event.get("eventAction") == "expiration":
                expiration = event.get("eventDate")
                break

        return {"method": "RDAP", "available": False, "expiration_date": expiration}

    except Exception as exc:
        return {"method": "RDAP", "available": None, "expiration_date": None, "error": str(exc)}
