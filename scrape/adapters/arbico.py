"""
ARBICO Organics — custom parser for gtag-embedded product data.

ARBICO embeds product/price data in Google Analytics 4 event schemas within
<script type="text/javascript"> blocks. The data is in a custom JSON structure
(not JSON-LD) with products listed in an "items" array containing:
  - item_name: product name (may contain HTML entities like &reg;)
  - item_id: SKU
  - price: dollar value (may be empty string)
  - item_brand: manufacturer
  - item_category: category name

The site structure:
  - Category pages: /category/{slug} — contains embedded product JSON
  - Product pages: /product/{slug}/{category} — contain detailed info & pricing

Prices are often included in category page JSON, though some items may have
empty prices in the listing (actual price must be fetched from product detail page).
"""
from __future__ import annotations

import html as html_module
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup  # type: ignore

from ..core.adapter import Adapter, register
from ..core.extractor import sniff_container


def _extract_gtag_products(html: str, page_url: str) -> list[dict]:
    """Extract products from gtag GA4 event data in <script> tags.

    Iterates through <script type="text/javascript"> blocks and finds
    all gtag product item objects. Extracts item_name, item_id (SKU),
    and price. Skips items with empty or zero prices.
    """
    rows: list[dict] = []
    seen_skus: set[str] = set()

    soup = BeautifulSoup(html, "lxml")
    for script in soup.find_all("script", type="text/javascript"):
        if not script.string:
            continue
        text = script.string

        # Find all item_name fields — the start of each product object
        item_starts = list(re.finditer(r'"item_name"\s*:', text))

        for match in item_starts:
            start_pos = match.start()
            # Look at the next ~500 chars to capture this item
            chunk = text[start_pos:start_pos + 500]

            # Extract item_name (may contain HTML entities like &reg;)
            name_match = re.search(
                r'"item_name"\s*:\s*"([^"]*(?:&[^;]*;[^"]*)*)"',
                chunk
            )
            if not name_match:
                continue
            name = html_module.unescape(name_match.group(1)).strip()
            if not name:
                continue

            # Extract item_id (SKU)
            id_match = re.search(r'"item_id"\s*:\s*"([^"]*)"', chunk)
            if not id_match:
                continue
            sku = id_match.group(1).strip()

            # Extract price (note the space before colon in JSON: "price" :  "12.95")
            price_match = re.search(r'"price"\s*:\s*"([^"]*)"', chunk)
            if not price_match:
                continue
            price_str = price_match.group(1).strip()

            # Skip empty prices
            if not price_str or price_str == "":
                continue

            try:
                price = float(price_str)
            except (ValueError, TypeError):
                continue

            # Skip zero or absurd prices
            if price <= 0 or price > 10_000:
                continue

            # Dedupe by SKU
            if sku in seen_skus:
                continue
            seen_skus.add(sku)

            rows.append({
                "name": name[:200],
                "price": price,
                "sku": sku,
                "url": page_url,
                "container": sniff_container(name),
                "raw_text": f"gtag:{sku}",
            })

    return rows


@register
class ARBICOAdapter(Adapter):
    supplier_id = 210
    supplier_name = "ARBICO Organics"
    requires_login = False
    prefer_tier = "curl_cffi"
    max_pages = 40  # Generous limit for many categories

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._visited_urls: set[str] = set()

    def start_urls(self) -> list[str]:
        """Start with major beneficial insects categories."""
        urls = [
            "https://www.arbico-organics.com/category/beneficial-insects-organisms",
            "https://www.arbico-organics.com/category/fly-control-program",
            "https://www.arbico-organics.com/category/organic-pest-control",
            "https://www.arbico-organics.com/category/fertilizers-soil-amendments",
            "https://www.arbico-organics.com/category/seeds-plants",
        ]
        # Initialize visited set with start URLs
        self._visited_urls.update(urls)
        return urls

    def parse_page(self, html: str, url: str) -> list[dict]:
        """Parse category pages for embedded gtag product data."""
        return _extract_gtag_products(html, url)

    def discover_urls(self, html: str, url: str) -> list[str]:
        """Discover subcategory links from category pages.

        Tracks visited URLs globally to prevent re-crawling cycles.
        Stops when max_pages limit is approached to prevent infinite loops.
        """
        soup = BeautifulSoup(html, "lxml")
        found: list[str] = []

        # Look for links that match /category/...
        for a in soup.find_all("a", href=True):
            href = a["href"]
            # Only follow category pages (not product pages)
            if href.startswith("/category/") and "-G" not in href:
                full_url = urljoin("https://www.arbico-organics.com", href)
                # Check against global visited set to prevent cycles
                if full_url not in self._visited_urls:
                    # Also check we're not exceeding page limit
                    if len(self._visited_urls) < self.max_pages:
                        self._visited_urls.add(full_url)
                        found.append(full_url)

        return found
