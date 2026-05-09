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
from urllib.parse import urldefrag, urljoin

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
    prefer_tier = "playwright"
    max_pages = 25

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
        """Parse category or product pages for embedded product data."""
        if "/product/" in url:
            row = self._extract_product_detail(html, url)
            return [row] if row else []
        return []

    def _extract_product_detail(self, html: str, url: str) -> dict | None:
        """Extract the main product from a detail page, excluding related items."""
        soup = BeautifulSoup(html, "lxml")
        title_el = soup.find("h1")
        title = title_el.get_text(" ", strip=True) if title_el else ""
        rows = _extract_gtag_products(html, url)
        if title and rows:
            normalized_title = _normalize_name(title)
            for row in rows:
                normalized_row = _normalize_name(row.get("name", ""))
                if normalized_title and (
                    normalized_title in normalized_row
                    or normalized_row in normalized_title
                ):
                    return row

        price_match = re.search(r"\bvar\s+price\s*=\s*(\d+(?:\.\d{1,2})?)\s*;", html)
        if title and price_match:
            price = float(price_match.group(1))
            if 0 < price < 10_000:
                return {
                    "name": title[:200],
                    "price": price,
                    "sku": "",
                    "url": url,
                    "container": sniff_container(title),
                    "raw_text": f"detail_var_price:{price}",
                }
        return None

    def discover_urls(self, html: str, url: str) -> list[str]:
        """Discover subcategory links from category pages.

        Tracks visited URLs globally to prevent re-crawling cycles.
        Stops when max_pages limit is approached to prevent infinite loops.
        """
        soup = BeautifulSoup(html, "lxml")
        found: list[str] = []

        if "/product/" in url:
            return found

        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/product/" not in href:
                continue
            full_url = urldefrag(urljoin("https://www.arbico-organics.com", href))[0]
            if full_url not in self._visited_urls and len(self._visited_urls) < self.max_pages:
                self._visited_urls.add(full_url)
                found.append(full_url)

        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not href.startswith("/category/") or "-G" in href:
                continue
            full_url = urldefrag(urljoin("https://www.arbico-organics.com", href))[0]
            if not _is_relevant_category_url(full_url):
                continue
            if full_url not in self._visited_urls and len(self._visited_urls) < self.max_pages:
                self._visited_urls.add(full_url)
                found.append(full_url)

        return found


def _normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", html_module.unescape(value).lower())


def _is_relevant_category_url(url: str) -> bool:
    slug = url.rsplit("/category/", 1)[-1].lower()
    keywords = (
        "beneficial", "insect", "organism", "fly", "organic-pest", "pest",
        "fertilizer", "soil", "amendment", "seed", "plant", "control",
    )
    return any(keyword in slug for keyword in keywords)
