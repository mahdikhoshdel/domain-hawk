from __future__ import annotations

import argparse
import json
from typing import Dict, Any

from .models import DomainResult
from .time_utils import now_iso, normalize_iso_utc
from .cache import load_cache, save_cache_atomic, is_stale
from .resolver import resolve_domain
from .config import DEFAULT_CACHE_PATH, DEFAULT_TTL_DAYS


def to_result(domain: str, payload: Dict[str, Any], source: str) -> DomainResult:
    return DomainResult(
        domain=domain,
        available=payload.get("available"),
        expiration_date=payload.get("expiration_date"),
        checked_at=payload.get("checked_at", now_iso()),
        method=payload.get("method", "unknown"),
        source=source,  # "cache" or "network"
        error=payload.get("error"),
    )


def lookup_domain(domain: str, cache_path: str, ttl_days: int, force_refresh: bool) -> DomainResult:
    cache = load_cache(cache_path)
    entry = cache.get(domain)

    if entry and not force_refresh and not is_stale(entry, ttl_days=ttl_days):
        return to_result(domain, entry, source="cache")

    info = resolve_domain(domain)
    checked_at = now_iso()

    if info.get("available") is not None:
        normalized_exp = normalize_iso_utc(info.get("expiration_date"))
        new_entry = {
            "available": info["available"],
            "expiration_date": normalized_exp,
            "checked_at": checked_at,
            "method": info.get("method", "unknown"),
        }
        cache[domain] = new_entry
        save_cache_atomic(cache, cache_path)
        return to_result(domain, new_entry, source="network")

    # error path
    error_entry = {
        "available": None,
        "expiration_date": None,
        "checked_at": checked_at,
        "method": info.get("method", "unknown"),
        "error": info.get("error"),
    }
    cache[domain] = error_entry
    save_cache_atomic(cache, cache_path)
    return to_result(domain, error_entry, source="network")


def refresh_all(cache_path: str, ttl_days: int) -> None:
    cache = load_cache(cache_path)
    if not cache:
        print("No cache yet. Nothing to refresh.")
        return

    changed = False
    for domain, entry in list(cache.items()):
        if is_stale(entry, ttl_days=ttl_days):
            info = resolve_domain(domain)
            checked_at = now_iso()
            if info.get("available") is not None:
                cache[domain] = {
                    "available": info["available"],
                    "expiration_date": normalize_iso_utc(info.get("expiration_date")),
                    "checked_at": checked_at,
                    "method": info.get("method", "unknown"),
                }
                print(f"Refreshed: {domain} ({cache[domain]['method']})")
                changed = True
            else:
                entry["checked_at"] = checked_at
                entry["error"] = info.get("error")
                print(f"Error refreshing {domain}: {info.get('error')}")
                changed = True

    if changed:
        save_cache_atomic(cache, cache_path)
        print("Cache updated.")
    else:
        print("All entries are fresh.")


def export_cache(cache_path: str, out_path: str) -> None:
    cache = load_cache(cache_path)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2, sort_keys=True)
    print(f"Exported cache to {out_path}")


def main() -> None:
    print("Lets go hunt ...")
    parser = argparse.ArgumentParser(
        description="Domain availability & expiration (RDAP-first; WHOIS fallback; cache-first)"
    )
    parser.add_argument("-d", "--domain", help="Single domain to lookup (cache-first).")
    parser.add_argument("--cache", default=DEFAULT_CACHE_PATH, help=f"Path to cache file (default {DEFAULT_CACHE_PATH}).")
    parser.add_argument("--ttl-days", type=int, default=DEFAULT_TTL_DAYS, help=f"Staleness TTL in days (default {DEFAULT_TTL_DAYS}).")
    parser.add_argument("--force-refresh", action="store_true", help="Bypass cache TTL for this lookup.")
    parser.add_argument("--refresh-all", action="store_true", help="Refresh stale entries in cache.")
    parser.add_argument("--export-json", metavar="PATH", help="Export current cache to JSON file at PATH.")
    args = parser.parse_args()

    if args.export_json:
        export_cache(args.cache, args.export_json)
        return

    if args.refresh_all:
        refresh_all(args.cache, args.ttl_days)
        return

    if args.domain:
        result = lookup_domain(args.domain, args.cache, args.ttl_days, args.force_refresh)
        if result.available is True:
            print(f"✅ {result.domain} is AVAILABLE [{result.method} | {result.source}]")
        elif result.available is False:
            print(f"❌ {result.domain} is TAKEN [{result.method} | {result.source}]")
            print(f"📅 Expiration: {result.expiration_date}")
            print(f"We can hunt it down in exact expiration date")
        else:
            print(f"⚠️ Error ({result.method} | {result.source}): {result.error}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()