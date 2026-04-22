"""
Shopify JSON API adapters.

Many Shopify stores expose a `/products.json` endpoint that returns
structured product data without needing HTML parsing or JS rendering.
This is faster, more reliable, and less detectable than scraping HTML.

API pagination: ?page=N&limit=250 (max 250 per page).
"""
from __future__ import annotations

import json
import logging
from urllib.parse import urljoin

from ..core.adapter import Adapter, register
from ..core.extractor import sniff_container
from ..core.fetcher import FetchResult, fetch
from ..core.stealth import human_delay

log = logging.getLogger("bloombox.shopify_json")


class ShopifyJSONAdapter(Adapter):
    """Base adapter for Shopify stores with public /products.json API."""

    # Subclasses set these
    base_url: str = ""          # e.g. "https://www.americanmeadows.com"
    collection_paths: list[str] = []  # e.g. ["/collections/all"]
    products_per_page: int = 250

    prefer_tier = "curl_cffi"
    requires_login = False

    def start_urls(self) -> list[str]:
        if self.collection_paths:
            return [
                f"{self.base_url}{path}/products.json?limit={self.products_per_page}"
                for path in self.collection_paths
            ]
        return [f"{self.base_url}/products.json?limit={self.products_per_page}"]

    def parse_page(self, html: str, url: str) -> list[dict]:
        """Parse Shopify JSON API response."""
        try:
            data = json.loads(html)
        except (json.JSONDecodeError, TypeError):
            log.warning("Non-JSON response from %s", url)
            return []

        products = data.get("products", [])
        rows: list[dict] = []
        seen: set[str] = set()

        for p in products:
            title = (p.get("title") or "").strip()
            if not title or len(title) > 200:
                continue

            handle = p.get("handle", "")
            product_url = f"{self.base_url}/products/{handle}" if handle else ""
            product_type = p.get("product_type", "")
            vendor = p.get("vendor", "")
            tags = p.get("tags", [])

            variants = p.get("variants") or []
            if not variants:
                continue

            for v in variants:
                price_str = v.get("price")
                if not price_str:
                    continue
                try:
                    price = float(price_str)
                except (ValueError, TypeError):
                    continue
                if price <= 0 or price > 10_000:
                    continue

                variant_title = (v.get("title") or "").strip()
                sku = v.get("sku") or ""
                available = v.get("available")
                in_stock = bool(available) if available is not None else None

                # Build a descriptive name
                if variant_title and variant_title != "Default Title":
                    name = f"{title} - {variant_title}"
                else:
                    name = title

                key = (name.lower(), price)
                if key in seen:
                    continue
                seen.add(key)

                rows.append({
                    "name": name[:200],
                    "price": price,
                    "sku": sku,
                    "url": product_url,
                    "in_stock": in_stock,
                    "container": sniff_container(name),
                    "category": product_type,
                    "raw_text": f"shopify_json:{price_str}",
                })

        return rows

    def discover_urls(self, html: str, url: str) -> list[str]:
        """Follow Shopify JSON pagination."""
        try:
            data = json.loads(html)
        except (json.JSONDecodeError, TypeError):
            return []

        products = data.get("products", [])
        if len(products) < self.products_per_page:
            return []  # last page

        # Parse current page number and build next
        import re
        page_match = re.search(r'[?&]page=(\d+)', url)
        current_page = int(page_match.group(1)) if page_match else 1
        next_page = current_page + 1

        if "?" in url and "page=" in url:
            next_url = re.sub(r'page=\d+', f'page={next_page}', url)
        elif "?" in url:
            next_url = f"{url}&page={next_page}"
        else:
            next_url = f"{url}?page={next_page}"

        return [next_url]

    def run(self):
        """Override run to handle JSON responses (not HTML)."""
        # The base run() works fine — fetch returns text which we parse as JSON
        return super().run()


# ---- REGISTERED SHOPIFY ADAPTERS ----------------------------------------

@register
class AmericanMeadowsAdapter(ShopifyJSONAdapter):
    supplier_id = 381
    supplier_name = "American Meadows"
    base_url = "https://www.americanmeadows.com"
    collection_paths = ["/collections/all"]
    max_pages = 8  # ~2000 products at 250/page


@register
class GrowellaAdapter(ShopifyJSONAdapter):
    supplier_id = 367
    supplier_name = "Growella"
    base_url = "https://growellshop.com"
    collection_paths = ["/collections/all"]
    max_pages = 4  # smaller catalog


# NOTE: Colorblends (SID 179)
# Tested April 2026: Shopify JSON API endpoints are NOT available.
# /products.json, /collections.json, and /collections/*/products.json all return
# HTML (React app shell) instead of JSON. The shop at shop.colorblends.com is a
# custom React-based storefront that does NOT use the standard Shopify JSON API.
# Would require undetected-chromedriver or Playwright to render and extract products.
# See generic.py for details — currently marked as DISABLED.
