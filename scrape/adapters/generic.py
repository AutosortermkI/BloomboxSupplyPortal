"""
Generic public-site adapters.

For suppliers whose prices are visible on a public catalog page, we can
register a one-line adapter that points at the start URL(s). The generic
extractor handles the rest (JSON-LD / product cards / regex fallback).

Sites with custom adapters (schroeder.py, walters.py, etc.) should NOT
appear here — they'd double-register.

Notes on sites *not* listed:
  - SID 129 (Schroeder Gardens) → schroeder.py (NOW PASSWORD-PROTECTED, April 2026)
  - SID 52  (Riggins Nursery) — PASSWORD-PROTECTED (April 2026). /complete-availability-prices
    is behind WordPress post password. Tested 4/13/26: returns password form only.
  - SID 179 (Colorblends) — WRONG URL (collection returns 404). Shop is at shop.colorblends.com
    and is JS-rendered (no HTML products). Needs undetected-chromedriver or Shopify API.
  - SID 202 (HC Companies) — NO PUBLIC PRICES. B2B catalog site with "request quote" model.
    Tested 4/13/26: /plant-pots/ and /products/ return info only, no pricing.
  - SID 210 (ARBICO Organics) → arbico.py (fixed April 2026: gtag product data)
  - SID 211 (Organic Mechanics) — PASSWORD-PROTECTED (April 2026). /shop/ returns password
    form. Tested 4/13/26: no product data accessible.
  - SID 178 (Van Engelen) — homepage is categories only, no product prices.
    Needs a custom adapter that crawls into /category/ pages.
  - SID 23  (Creek Hill) — Joomla nav shell, availability is JS-rendered.
    Needs playwright + custom discovery. Deferred until we verify yield.
  - SID 59  (Lucas Greenhouses) — 12KB shell, content JS-rendered.
    Deferred — returns nothing even via playwright without waitForSelector.
  - SID 61  (DV Flora) — wholesale, prices hidden behind login ("Read more"
    buttons, no dollar values on any public page). Move to login-gated.
  - SID 27  (Miller Plant Farm) — no prices in public HTML at all.
  - SID 36  (Clear Ridge) — no prices in public HTML; probably PDF avail list.
  - SID 207 (SiteOne) → siteone.py (hidden input price fields)
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup  # type: ignore

from ..core.adapter import Adapter, register
from ..core.extractor import extract_prices_from_html


def _simple(sid: int, name: str, urls: list[str], *,
            login: bool = False, tier: str | None = None,
            max_pages: int = 15) -> type[Adapter]:
    """Factory that builds and registers a trivial Adapter subclass."""
    cls_name = f"Adapter_{sid}"
    cls = type(cls_name, (Adapter,), {
        "supplier_id": sid,
        "supplier_name": name,
        "requires_login": login,
        "prefer_tier": tier,
        "max_pages": max_pages,
        "start_urls": lambda self: urls,
    })
    return register(cls)


# ---- Helper for adapters that need URL discovery from category pages ----
def _crawling(sid: int, name: str, urls: list[str], *,
              link_pattern: str, tier: str | None = None,
              max_pages: int = 20) -> type[Adapter]:
    """Factory for adapters that discover product pages from a category index.

    `link_pattern` is a regex matched against <a href>. Matching links are
    queued for visiting and extracted on subsequent pages.
    """
    _pat = re.compile(link_pattern)

    def _discover(self, html: str, url: str) -> list[str]:
        soup = BeautifulSoup(html, "lxml")
        found = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if _pat.search(href):
                full = urljoin(url, href)
                if full not in found:
                    found.append(full)
        return found

    cls_name = f"CrawlAdapter_{sid}"
    cls = type(cls_name, (Adapter,), {
        "supplier_id": sid,
        "supplier_name": name,
        "requires_login": False,
        "prefer_tier": tier,
        "max_pages": max_pages,
        "start_urls": lambda self: urls,
        "discover_urls": _discover,
    })
    return register(cls)


# ---- PUBLIC-PRICING SUPPLIERS ----

# SiteOne: has its own adapter in siteone.py (hidden input price fields)

# Colorblends: Shopify storefront at shop.colorblends.com, not on main domain.
# Main domain (www.colorblends.com) is a WordPress marketing site, not e-commerce.
# DISABLED April 2026: Tested all Shopify JSON API endpoints (/products.json,
# /collections.json, /collections/*/products.json) — all return HTML (React app shell).
# This is a custom React-based storefront that does NOT expose the standard Shopify
# JSON API. The shop is JS-rendered and requires undetected-chromedriver or Playwright
# to render. Collections (/tulips, /daffodils) also don't work via HTML scraping.
# Status: DISABLED — not scrapeable with standard adapters.
# _simple(179, "Colorblends Bulbs",
#         ["https://shop.colorblends.com/collections/tulips",
#          "https://shop.colorblends.com/collections/daffodils"],
#         tier="undetected")

# ARBICO Organics → arbico.py (custom adapter)
# Product data is embedded in Google Analytics 4 event JSON within category pages.
# The site embeds gtag product arrays with prices in <script type="text/javascript">.
# This is not JSON-LD format, so a custom parser is needed.

# Organic Mechanics: Shop page is password-protected (WordPress post-password-required).
# Cannot access product listings without valid password.
# Tested April 2026: /shop/ returns password form, no product data.
# Status: DISABLED - requires authentication.
# _simple(211, "Organic Mechanics Soil",
#         ["https://organicmechanicsoil.com/shop/"],
#         tier="curl_cffi")

# Riggins: Availability page is password-protected (WordPress post-password-required).
# Tested April 2026: /complete-availability-prices returns password form only.
# No product data accessible without credentials.
# Status: DISABLED - requires authentication.
# _simple(52, "Riggins Nursery",
#         ["https://www.riggins-nursery.com/complete-availability-prices"],
#         tier="playwright")

# HC Companies: B2B catalog site with NO PUBLIC PRICES.
# Tested April 2026: /plant-pots/ and /products/ return catalog info only.
# No pricing visible in HTML; this is a "request a quote" wholesale vendor.
# Status: DISABLED - not scrapeable (quote-based model, no public prices).
# _simple(202, "HC Companies",
#         ["https://hc-companies.com/plant-pots/",
#          "https://hc-companies.com/products/"],
#         tier="curl_cffi")

# ---- LOGIN-GATED (queued for vault integration, no public prices) ----
# These suppliers require an account to see pricing. They'll be enabled
# once Joe gets credentials entered into the vault.
#
# _simple(61,  "DV Flora",         [...], login=True)
# _simple(27,  "Miller Plant Farm", [...], login=True)
# _simple(36,  "Clear Ridge Nursery", [...], login=True)
# _simple(178, "Van Engelen Bulbs",  [...], login=True)
# _simple(16,  "Quality Greenhouses", [...], login=True)  # epicas portal

# ---- CUSTOM ADAPTERS (have their own .py files) ----
# SID 129 (Schroeder Gardens) → schroeder.py
# SID 207 (SiteOne)           → siteone.py
# SID 210 (ARBICO Organics)   → arbico.py
# SID 312 (Cactus King)       → cactusking.py
# SID 379 (Prairie Moon)      → prairiemoon.py
# SID 381 (American Meadows)  → shopify_json.py
# SID 367 (Growella)          → shopify_json.py

# ---- NO PUBLIC PRICING / QUOTE-BASED ----
# Investigated April 2026 — these "public" sites have no scrapeable prices:
# SID   3 (Brandywine Trees)       — WooCommerce but quote-based, no prices
# SID   8 (Highland Hill Farm)     — digatree.com offline/blocking
# SID   9 (Clearview Nursery)      — external Plantiful B2B portal, no public prices
# SID  11 (Gro 'n Sell)            — B2B portal only (epicas.gro-n-sell.com)
# SID  15 (Edge of the Woods)      — info site only, no e-commerce
# SID 131 (Esbenshade's)           — SSL cert error / not accessible
# SID 135 (Holly Days Nursery)     — 403 Forbidden
# SID 165 (TreeWorld Wholesale)    — WooCommerce but quote-based, no prices
# SID 209 (Meadow Fresh Perennials) — site offline
# SID 212 (Bucks County Perennial)  — site offline
# SID 213 (Reading Wholesale)       — JS redirect, unclear
# SID 220 (Union County Wholesale)  — site offline
# SID 223 (Schuylkill Valley)       — site offline
# SID 234 (Kent County Perennial)   — site offline
# SID 240 (Atlantic County)         — site timeout
# SID 306 (HeadStart Nursery)       — WooCommerce, no visible prices
# SID 351 (Tennessee Plant Co)      — site offline
# SID 380 (Stock Seed Farms)        — custom .NET, prices hidden/API-only
# SID 389 (Ernst Conservation Seeds) — timeout, duplicate of SID 21 (PDF)

# ---- HARD GOODS / INDUSTRIAL (no scrapeable product prices) ----
# SID 356 (Dillen Products)         — redirects to HC Companies
# SID 357 (HC Companies)            — duplicate of SID 202, no public prices
# SID 358 (ICL Fertilizers)         — site offline
# SID 359 (Haifa Chemicals)         — domain parked
# SID 360 (Scotts Osmocote)         — scotts.com, maintenance mode
# SID 363 (GRODAN)                  — B2B info hub, no product prices
# SID 390 (American Botanical)      — site offline
