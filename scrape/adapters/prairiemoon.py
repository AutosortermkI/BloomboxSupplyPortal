"""
Prairie Moon Nursery — Miva Merchant e-commerce platform.

Prairie Moon uses Miva's JSON API to load product data client-side.
The static HTML contains only placeholder content; actual prices are
rendered via JavaScript from `mm5/json.mvc` endpoints.

Strategy: Use Playwright to render the page and wait for product
cards to appear, then parse the rendered DOM.

Categories: Seeds, Plants, Mixes, Tools/Books.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup  # type: ignore

from ..core.adapter import Adapter, register
from ..core.extractor import parse_price, sniff_container

_PRICE_IN_TEXT = re.compile(r"\$\s?(\d{1,4}(?:,\d{3})*(?:\.\d{1,2})?)")


@register
class PrairieMoonAdapter(Adapter):
    supplier_id = 379
    supplier_name = "Prairie Moon Nursery"
    requires_login = False
    prefer_tier = "playwright"
    wait_for = ".product-list .product-name, .x-product-list-item"
    max_pages = 6

    def start_urls(self) -> list[str]:
        return [
            "https://www.prairiemoon.com/seeds/wildflowers/?Per_Page=48",
            "https://www.prairiemoon.com/seeds/grasses/?Per_Page=48",
            "https://www.prairiemoon.com/plants/?Per_Page=48",
        ]

    def parse_page(self, html: str, url: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        rows: list[dict] = []
        seen: set[str] = set()

        # Miva rendered product cards — multiple possible selectors
        # depending on theme version
        card_selectors = [
            ".x-product-list-item",
            ".product-list-item",
            "[data-product-code]",
            ".product-item",
            ".category-product",
        ]

        cards = []
        for sel in card_selectors:
            cards = soup.select(sel)
            if cards:
                break

        for card in cards:
            # Product name
            name = ""
            for name_sel in [
                ".product-name a", ".x-product-list-name a",
                "h3 a", "h4 a", ".product-title a", "a.product-name",
            ]:
                el = card.select_one(name_sel)
                if el:
                    name = el.get_text(strip=True)
                    break
            if not name:
                # Try any heading
                for h in card.find_all(["h2", "h3", "h4"]):
                    t = h.get_text(strip=True)
                    if t and len(t) > 3:
                        name = t
                        break
            if not name or len(name) > 200:
                continue

            # Product URL
            product_url = url
            link = card.find("a", href=True)
            if link:
                product_url = urljoin(url, link["href"])

            # Price
            price = None
            for price_sel in [
                ".product-price", ".x-product-list-price",
                ".price", ".money", "span.price",
            ]:
                el = card.select_one(price_sel)
                if el:
                    price = parse_price(el.get_text(strip=True))
                    if price:
                        break

            # Fallback: search all text in the card for a $ amount
            if price is None:
                text = card.get_text(" ", strip=True)
                m = _PRICE_IN_TEXT.search(text)
                if m:
                    try:
                        price = float(m.group(1).replace(",", ""))
                    except ValueError:
                        pass

            if price is None or price <= 0 or price > 5000:
                continue

            key = (name.lower(), price)
            if key in seen:
                continue
            seen.add(key)

            rows.append({
                "name": name[:200],
                "price": price,
                "url": product_url,
                "container": sniff_container(name),
                "raw_text": f"miva:{price}",
            })

        # Fallback: if no cards found, try generic extraction
        if not rows:
            from ..core.extractor import extract_prices_from_html
            rows = extract_prices_from_html(html, url)

        return rows

    def discover_urls(self, html: str, url: str) -> list[str]:
        """Follow Miva pagination."""
        soup = BeautifulSoup(html, "lxml")
        found: list[str] = []
        # Miva uses ?Offset=N or ?Per_Page=N&Page=N
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if ("Offset=" in href or "Page=" in href) and "prairiemoon.com" in href:
                full = urljoin(url, href)
                if full not in found and full != url:
                    found.append(full)
        # Also look for "next" pagination links
        for a in soup.find_all("a", href=True):
            classes = a.get("class", [])
            text = a.get_text(strip=True).lower()
            if "next" in text or "x-pagination-next" in " ".join(classes):
                full = urljoin(url, a["href"])
                if full not in found and full != url:
                    found.append(full)
        return found
