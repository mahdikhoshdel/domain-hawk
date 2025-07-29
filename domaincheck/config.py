from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
import yaml
import pathlib


DEFAULT_CACHE_PATH = "domains_cache.json"
DEFAULT_WHOIS_CONFIG_PATH = "whois_servers.yml"
IANA_WHOIS_HOST = "whois.iana.org"

# Cache policy
DEFAULT_TTL_DAYS = 7
NEAR_EXPIRY_DAYS = 60
NEAR_EXPIRY_TTL_DAYS = 1

REQUEST_TIMEOUT_SECONDS = 6


@dataclass(frozen=True)
class WhoisDefaults:
    timeout_seconds: int
    follow_referral: bool
    generic_not_found_patterns: List[str]
    generic_expiry_patterns: List[str]


@dataclass(frozen=True)
class TldConfig:
    server: str | None
    query_format: str
    not_found_patterns: List[str]
    expiry_patterns: List[str]


def load_whois_config(path: str = DEFAULT_WHOIS_CONFIG_PATH) -> tuple[WhoisDefaults, dict[str, TldConfig]]:
    file = pathlib.Path(path)
    if not file.exists():
        return (
            WhoisDefaults(
                timeout_seconds=6,
                follow_referral=True,
                generic_not_found_patterns=["no match", "not found", "status: free", "no data found", "nothing found"],
                generic_expiry_patterns=[
                    r"(?:Expiry|Expiration|Expire|paid-till|paid till|renewal date)[:\s]*([0-9]{4}[-/.][0-9]{2}[-/.][0-9]{2}(?:[ T][0-9]{2}:[0-9]{2}:[0-9]{2}Z?)?)",
                    r"(?:expires on|expires)[:\s]*([A-Za-z]{3,9}\s+[0-9]{1,2},\s*[0-9]{4})",
                ],
            ),
            {},
        )

    data: Dict[str, Any] = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
    d = data.get("defaults", {}) or {}
    defaults = WhoisDefaults(
        timeout_seconds=int(d.get("timeout_seconds", 6)),
        follow_referral=bool(d.get("follow_referral", True)),
        generic_not_found_patterns=list(d.get("generic_not_found_patterns", [])),
        generic_expiry_patterns=list(d.get("generic_expiry_patterns", [])),
    )

    tlds_cfg: dict[str, TldConfig] = {}
    for tld, cfg in (data.get("tlds", {}) or {}).items():
        tlds_cfg[tld.lower()] = TldConfig(
            server=cfg.get("server"),
            query_format=cfg.get("query_format", "{domain}\r\n"),
            not_found_patterns=list(cfg.get("not_found_patterns", [])),
            expiry_patterns=list(cfg.get("expiry_patterns", [])),
        )

    return defaults, tlds_cfg
