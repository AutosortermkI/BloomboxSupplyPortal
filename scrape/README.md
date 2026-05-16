# BloomBox Live Price Scraper

A 3-tier, stealth-oriented scraping framework that feeds live wholesale prices
into the Supplier Portal tab of the BloomBox dashboard.

## Architecture

```
scrape/
├── credentials.py  ← local credential helper (metadata + macOS Keychain)
├── ADAPTER_AUDIT.md ← current production/scaffold/placeholder classifications
├── core/
│   ├── fetcher.py     ← 3-tier cascade (curl_cffi → Playwright → undetected-chromedriver)
│   ├── stealth.py     ← UA rotation, human delays, cookie persistence, proxy hooks
│   ├── vault.py       ← reads local credential metadata + OS-stored passwords
│   ├── extractor.py   ← generic price extraction (JSON-LD → product cards → regex)
│   └── adapter.py     ← base class + @register decorator
├── adapters/
│   ├── generic.py     ← one-line adapters for public-pricing suppliers
│   └── walters.py     ← login-required adapter scaffold (Walters Gardens #110)
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

**Run from inside `scrape/` (simplest):**

```bash
cd ~/BloomboxSupplyPortal/scrape
source .venv/bin/activate

python run.py --dry-run            # list adapters, don't fetch
python run.py --preflight          # dependency and browser-tier readiness check
python run.py --public             # all public-pricing suppliers
python run.py --logged-in          # only suppliers with stored creds
python run.py --id 207 178 179     # specific supplier IDs
python run.py --public --concurrency 1 -v   # verbose + serial for debugging
```

**Or from the repo root with `-m` (needed if you're scripting):**

```bash
cd ~/BloomboxSupplyPortal
source scrape/.venv/bin/activate
python -m scrape.run --public -v
```

Note: `python -m scrape.run` will **not** work from inside `scrape/`
itself — `-m` resolves the `scrape` package name before the script runs,
and it can't see it from one level down. Use `python run.py` there, or
`cd ..` first.

After a successful run:

- `scrape/output/prices.json` — canonical feed
- `prices.js` at the repo root — the dashboard loads this automatically
  (reload `index.html` to see the "LIVE PRICE FEED" banner in the
  Supplier Portal tab)
- `scrape/output/history/<YYYYMMDD>.json` — daily archive

## Preflight and publish safety

- Run `python -m scrape.run --preflight` before unattended jobs on a new machine.
  It reports whether Playwright and undetected-chromedriver tiers are actually
  installed for the selected adapters.
- By default, an empty run will **not** overwrite an existing `prices.json` /
  `prices.js` live feed. This prevents a broken adapter or half-configured
  environment from wiping out the last good dashboard feed.
- If you intentionally want to publish an empty feed, pass
  `--allow-empty-publish`.

## Credentials

The dashboard is not a password vault. It stores only non-secret login metadata
for buyer workflow convenience. The scraper runner reads:

- non-secret metadata from `~/.config/bloombox/credentials.json`
- passwords from macOS Keychain

Add one credential:

```bash
cd ~/BloomboxSupplyPortal
python3 -m scrape.credentials set \
  --id 110 \
  --url https://www.waltersgardens.com/customer/account/login/ \
  --user "$BLOOMBOX_WALTERS_USERNAME"
```

The command prompts for the supplier password. To inspect configured metadata
without printing secrets:

```bash
python3 -m scrape.credentials list
```

That command is the source of truth for whether the Python runtime can see a
Keychain-backed credential. The static dashboard cannot read macOS Keychain
directly and may show zero browser metadata even when the scraper is fully
credentialed.

### Manual login session capture

For suppliers with a CAPTCHA or other human approval step, do not automate the
challenge. Use a headed Playwright handoff, complete the login manually in the
opened browser, then let the scraper save reusable storage state:

```bash
python3 -m scrape.credentials login-session \
  --id 43 \
  --success-text "Log out" \
  --success-text "Account details"
```

The helper prefills the saved username/password from the local credential
store, never clicks CAPTCHA controls, and writes the authenticated Playwright
storage state under `scrape/cache/sessions/`. That directory is ignored by git.
Future Playwright-tier fetches for the supplier automatically load that state
when it exists.

Legacy plaintext dashboard vault exports are not auto-discovered anymore.
They are accepted only when explicitly selected:

```bash
BLOOMBOX_VAULT_PATH="$HOME/Downloads/bloombox_vault_2026-04-27.json" \
python3 -m scrape.run --logged-in
```

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

**Login required:** see `adapters/walters.py` for the current scaffold. It
still needs verification against a real approved supplier account before it
should be treated as production-grade.

## Scheduling and deployment model

The current deployable shape is a local internal tool:

- run the static dashboard from disk or serve it as static files
- run scraper jobs on a private local or server-side machine
- publish only generated feed artifacts (`prices.js` / `prices.json`) to the
  dashboard location
- keep supplier credentials out of any hosted static dashboard

```bash
# Example local launchd/cron payload once adapter quality is known:
cd ~/BloomboxSupplyPortal && scrape/.venv/bin/python -m scrape.run --public --logged-in
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
