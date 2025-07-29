
---

# Domain Hawk
**"Attention: Your domain is under the Hawk's watch."**

A powerful RDAP-first domain monitoring and expiration tracker with smart caching.

* **RDAP‑first** for accuracy and structured data.
* **Config‑driven WHOIS fallback** for TLDs without RDAP.
* **Smart caching** with auto‑refresh policy (more frequent near expiry).
* **CLI tool** with single lookups and scheduled refresh.
* **IDN (Unicode) domains supported** via punycode.

---

## Features

* ✅ Check **availability** (registered or free).
* ✅ Get **expiration date** when available from RDAP/WHOIS.
* ✅ **Cache** results to `domains_cache.json` and reuse until stale.
* ✅ **Auto‑refresh** cadence: weekly by default, **daily** when <60 days to expiration.
* ✅ **YAML config** for WHOIS behavior per TLD (server, query, not‑found regex, expiry regex).
* ✅ Works with **Unicode/IDN** domains (converts to punycode).

---

## Requirements

* Python **3.10+**
* Packages: `requests`, `PyYAML`, `idna`

Install:

```bash
pip install -r requirements.txt
```

---

## Project Structure

```
domaincheck/
├─ domaincheck/
│  ├─ __init__.py
│  ├─ cli.py             # CLI entry point
│  ├─ cache.py           # cache I/O and staleness policy
│  ├─ models.py          # typed result model
│  ├─ resolver.py        # RDAP-first; WHOIS fallback
│  ├─ rdap_client.py     # RDAP queries
│  ├─ whois_client.py    # WHOIS queries & parsing (config-driven)
│  ├─ time_utils.py      # UTC/ISO helpers
│  └─ config.py          # config constants and YAML loader
├─ whois_servers.yml     # WHOIS fallback configuration
├─ domains_cache.json    # (created automatically)
└─ README.md
```

---

## Quick Start

From the project root:

```bash
# 1) Create and activate a virtual environment (optional but recommended)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 2) Install dependencies
pip install requests pyyaml idna

# 3) Run a single lookup (cache-first)
python -m domaincheck.cli -d example.com
```

**Example outputs:**

* Available:

  ```
  ✅ example123-rare.com is AVAILABLE [RDAP | network]
  ```
* Taken:

  ```
  ❌ example.com is TAKEN [RDAP | network]
  📅 Expiration: 2028-09-13T04:00:00Z
  ```

---

## CLI Usage

```bash
python -m domaincheck.cli [options]
```

**Options:**

* `-d, --domain DOMAIN`
  Check a single domain (cache‑first).

* `--force-refresh`
  Ignore TTL and query network even if the cache is fresh.

* `--cache PATH`
  Path to cache file (default `domains_cache.json`).

* `--ttl-days N`
  Staleness TTL in days (default `7`). Entries near expiry (< 60 days) refresh daily regardless.

* `--refresh-all`
  Refresh **only stale** cache entries (use this for scheduled runs).

* `--export-json PATH`
  Export current cache to a JSON file.

**Examples:**

```bash
# Single check (cache-first)
python -m domaincheck.cli -d example.com

# Force a fresh network check
python -m domaincheck.cli -d example.com --force-refresh

# Refresh stale entries in the cache (for scheduling)
python -m domaincheck.cli --refresh-all

# Export cache
python -m domaincheck.cli --export-json cache_dump.json

# Custom cache path
python -m domaincheck.cli -d example.com --cache .data/domains.json
```

> **Tip:** You can also run directly as a script if you added the small top‑of‑file package snippet in `cli.py`.
> Best practice is `python -m domaincheck.cli`.

---

## Cache File Format

`domains_cache.json` (auto‑created) maps each domain to a record:

```json
{
  "example.com": {
    "available": false,
    "expiration_date": "2028-09-13T04:00:00Z",
    "checked_at": "2025-07-29T10:00:00Z",
    "method": "RDAP"
  },
  "example.ir": {
    "available": false,
    "expiration_date": "expire-date: 1404-03-06",
    "checked_at": "2025-07-29T10:01:00Z",
    "method": "WHOIS"
  }
}
```

* `method` is `"RDAP"` or `"WHOIS"`.
* `checked_at` is ISO‑8601 UTC with trailing `Z`.
* `expiration_date` is ISO‑UTC when parsable; otherwise a registry raw value or `null`.

---

## RDAP vs WHOIS

* The resolver uses **RDAP first** (modern, structured).
* If a TLD has **no RDAP endpoint** (e.g., `.ir`), it uses **WHOIS fallback** based on `whois_servers.yml`.

**Known limitations**

* Some registries **do not publish** expiration in WHOIS/RDAP (e.g., `.de`), so you may get availability but not expiry.
* WHOIS responses vary by TLD/registry; tune regex patterns in the YAML if expiry is not extracted.

---

## Configuring WHOIS Fallback

Edit `whois_servers.yml` to add/adjust TLD behavior:

```yaml
defaults:
  timeout_seconds: 6
  follow_referral: true
  generic_not_found_patterns:
    - "no match"
    - "not found"
    - "status: free"
    - "no data found"
    - "nothing found"
  generic_expiry_patterns:
    - "(?:Expiry|Expiration|Expire|paid-till|paid till|renewal date)[:\\s]*([0-9]{4}[-/.][0-9]{2}[-/.][0-9]{2}(?:[ T][0-9]{2}:[0-9]{2}:[0-9]{2}Z?)?)"
    - "(?:expires on|expires)[:\\s]*([A-Za-z]{3,9}\\s+[0-9]{1,2},\\s*[0-9]{4})"

tlds:
  ir:
    server: whois.nic.ir
    query_format: "{domain}\r\n"
    not_found_patterns: ["no entries found", "no match"]
    expiry_patterns:
      - "(?:expire date|expiration date|expiry date)[:\\s]*([0-9]{4}-[0-9]{2}-[0-9]{2})"
      - "(?:expire-date)[:\\s]*([0-9]{4}-[0-9]{2}-[0-9]{2})"

  me:
    server: whois.nic.me
    query_format: "{domain}\r\n"
    not_found_patterns: ["no match for"]
    expiry_patterns:
      - "expiry date:\\s*([0-9]{4}-[0-9]{2}-[0-9]{2}t[0-9]{2}:[0-9]{2}:[0-9]{2}z?)"
      - "expiry date:\\s*([0-9]{4}-[0-9]{2}-[0-9]{2})"
```

**Fields:**

* `server`: WHOIS host to query (port 43).
* `query_format`: sent to the server; `{domain}` is replaced.
* `not_found_patterns`: lowercase match substrings for availability.
* `expiry_patterns`: regex list to capture an expiry string (first capture group wins).

If `server` is omitted, the code asks **IANA WHOIS** and follows referral if present.

---

## Scheduling

### Windows (Task Scheduler)

Refresh stale cache daily at 09:00:

1. Open **Task Scheduler** → **Create Task**.
2. **Triggers** → New → Daily at 09:00.
3. **Actions** → New:

   * **Program/script:** path to your **venv** Python, e.g.
     `C:\path\to\domain-hawk\.venv\Scripts\python.exe`
   * **Add arguments:**
     `-m domaincheck.cli --refresh-all`
   * **Start in:** project folder, e.g.
     `C:\path\to\domain-hawk`
4. Save.

### Linux/macOS (cron)

```bash
# Refresh at 09:00 daily
0 9 * * * /usr/bin/python3 -m domaincheck.cli --refresh-all >> /var/log/domaincheck_refresh.log 2>&1
```

---

## Troubleshooting

* **“attempted relative import with no known parent package”**
  Run as a module from project root:
  `python -m domaincheck.cli -d example.com`
  Or add the small package bootstrap snippet at the top of `cli.py`.

* **No output**
  Ensure `if __name__ == "__main__": main()` exists at the bottom of `cli.py`.
  Try `--force-refresh` to bypass cache TTL.
  Add temporary prints in `main()` to confirm it runs.

* **No RDAP for a TLD**
  That’s normal for some ccTLDs (e.g., `.ir`). Configure WHOIS in `whois_servers.yml`.

* **No expiration shown**
  The registry might not publish it, or regex needs to be tuned for that TLD.
  Add/adjust `expiry_patterns` for that TLD in the YAML.

---

## License

MIT (or your preferred license). Add a `LICENSE` file if needed.

---

## Maintainer Notes

* Keep `whois_servers.yml` updated for TLDs you care about.
* Consider rate limits for heavy WHOIS usage—your **cache & scheduled refresh** help minimize calls.
* For bulk monitoring, you can list the domains in the cache and rely on `--refresh-all` to keep them up to date.

---
