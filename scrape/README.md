# BloomBox Live Price Scraper

A 3-tier, stealth-oriented scraping framework that feeds live wholesale prices
into the Supplier Portal tab of the BloomBox dashboard.

## Architecture

```
scrape/
├── core/
│   ├── fetcher.py     ← 3-tier cascade (curl_cffi → Playwright → undetected-chromedriver)
│   ├── stealth.py     ← UA rotation, human delays, cookie persistence, proxy hooks
│   ├── vault.py       ← reads credentials exported from dashboard Supplier Portal
│   ├── extractor.py   ← generic price extraction (JSON-LD → product cards → regex)
│   └── adapter.py     ← base class + @register decorator
├── adapters/
│   ├── generic.py     ← one-line adapters for public-pricing suppliers
│   └── walters.py     ← example login-required adapter (Walters Gardens #110)
├── run.py             ← CLI runner with concurrency, filters, archival
├── output/
│   ├── prices.json    ← latest merged feed
│   ├── prices.js      ← same data as `window.LIVE_PRICES` for the dashboard
│   ├── run_summary.json
│   └── history/       ← daily archived snapshots
└── cache/sessions/    ← per-supplier cookie jars
```

## Why a 3-tier cascade?

Different suppliers deploy different levels of anti-bot tech. Rather than
always reaching for the slowest/heaviest tool, the fetcher escalates only
when needed:

1. **`curl_cffi`** (tier 1) — an HTTP client that impersonates real Chrome
   TLS/JA3 fingerprints. Fast, cheap, and beats Cloudflare on the vast
   majority of independent nursery sites.
2. **Playwright + stealth** (tier 2) — real headless Chromium with
   `navigator.webdriver` patched out, plus randomized viewport, locale,
   timezone, mouse scrolling, and dwell time. Used when tier 1 returns a
   block page or empty content.
3. **`undetected-chromedriver`** (tier 3) — Selenium-based, with a patched
   Chrome binary designed specifically to bypass hardened detection
   (PerimeterX, DataDome, etc.). Slowest but most reliable.

Each tier saves cookies on success so the next run starts authenticated.

## Setup (one-time)

```bash
cd ~/BloomboxSupplyPortal/scrape
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Usage

```bash
# Dry-run — list adapters matching the filter without fetching
python -m scrape.run --dry-run

# Run only the public-pricing suppliers (no login required)
python -m scrape.run --public

# Run only suppliers where credentials are stored in the vault
python -m scrape.run --logged-in

# Run specific supplier IDs
python -m scrape.run --id 207 178 179

# Verbose logging, serial (concurrency=1 to avoid tier conflicts when debugging)
python -m scrape.run --public --concurrency 1 -v
```

After a successful run:

- `scrape/output/prices.json` — canonical feed
- `prices.js` at the repo root — the dashboard loads this automatically
  (reload `index.html` to see the "LIVE PRICE FEED" banner in the
  Supplier Portal tab)
- `scrape/output/history/<YYYYMMDD>.json` — daily archive

## Credential vault

Credentials live on your machine only. Export them from the dashboard:

1. Open `index.html` → **Supplier Portal** tab
2. Click on a login-required supplier row to expand
3. Fill in login URL / username / password / account # → **Save Credentials**
4. Click **Export Vault JSON** to download `bloombox_vault_<date>.json`
5. Move that file to `~/Downloads/` (default) or set `BLOOMBOX_VAULT_PATH`
   to its location

The runner automatically loads the most recent export.

## Adding a new supplier adapter

**Public site, generic extractor works:** one line in `adapters/generic.py`.

```python
_simple(207, "SiteOne Landscape Supply",
        ["https://www.siteone.com/en/catalog/category/nursery/"],
        tier="playwright")
```

**Public site, needs custom parsing:** subclass `Adapter` directly.

```python
from ..core.adapter import Adapter, register

@register
class MyAdapter(Adapter):
    supplier_id = 123
    supplier_name = "Example Nursery"
    prefer_tier = "curl_cffi"

    def start_urls(self):
        return ["https://example.com/catalog"]

    def parse_page(self, html, url):
        # custom extraction logic
        ...
```

**Login required:** see `adapters/walters.py` for the pattern.

## Scheduling (later)

Once the manual runs are stable, wire it into a scheduled task with the
Cowork `schedule` skill or a plain cron/launchd entry. Recommended:
nightly at 3am local.

```bash
# Example cron
0 3 * * * cd ~/BloomboxSupplyPortal && .venv/bin/python -m scrape.run --public --logged-in
```

## Proxy rotation (optional)

Set `BLOOMBOX_PROXIES` to a comma-separated list of proxy URLs:

```bash
export BLOOMBOX_PROXIES="http://user:pass@proxy1:8080,http://user:pass@proxy2:8080"
python -m scrape.run --public
```

`stealth.get_proxy()` picks one at random per request. Residential proxies
recommended if any supplier starts blocking you.

## Ethics and rate limits

- Default delays (1.5–4.5s between pages) are tuned to be lower-than-human
  but not aggressive. Bump them for polite scraping.
- Session cookies are cached per-supplier so we don't re-auth unnecessarily.
- Never run >2 concurrent workers against the same supplier.
- If a supplier explicitly asks you to stop (email, ToS amendment), just
  remove the adapter.
