"""
Schroeder Gardens — PASSWORD-PROTECTED (April 2026).

IMPORTANT: The shop page at https://www.schroedergardens.com/shop
is password-protected (WordPress post-password-required). No product
data is accessible without valid credentials.

Legacy note: The code below targets Wix/React data-hook attributes and
was written to extract product prices, but the content is now gated.

Status: DISABLED - requires authentication.
Credentials needed to unlock the shop before scraping can resume.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup  # type: ignore

from ..core.adapter import Adapter, register
from ..core.extractor import ProductRow, sniff_container, parse_price

_PRICE_IN_TEXT = re.compile(r"\$\s?(\d{1,4}(?:,\d{3})*(?:\.\d{1,2})?)")


@register
class SchroederAdapter(Adapter):
    supplier_id = 129
    supplier_name = "Schroeder Gardens"
    requires_login = True  # NOW PASSWORD-PROTECTED (April 2026)
    prefer_tier = "playwright"
    wait_for = "[data-hook='product-item-root']"  # Wait for Wix to render products
    max_pages = 5

    def start_urls(self) -> list[str]:
        # Shop page is password-protected as of April 2026
        # Cannot access without valid WordPress post password
        return ["https://www.schroedergardens.com/shop"]

    def parse_page(self, html: str, url: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        rows: list[dict] = []
        seen: set[str] = set()

        for card in soup.select('[data-hook="product-item-root"]'):
            # Name: from alt text on image, or from the details div
            name = ""
            img = card.select_one("img[alt]")
            if img and img.get("alt"):
                name = img["alt"].strip()
            if not name:
                details = card.select_one(
                    '[data-hook="product-item-product-details"]'
                )
                if details:
                    name = details.get_text(" ", strip=True)

            if not name or len(name) > 200:
                continue

            # Price: extract from the price-to-pay element
            price_el = card.select_one(
                '[data-hook="sr-product-item-price-to-pay"]'
            )
            price_text = price_el.get_text(strip=True) if price_el else ""
            # Handle "Price$35.00" format — just find the $ amount
            price = parse_price(price_text)
            if price is None:
                m = _PRICE_IN_TEXT.search(price_text)
                if m:
                    try:
                        price = float(m.group(1).replace(",", ""))
                    except ValueError:
                        continue
            if price is None or price <= 0 or price > 5000:
                continue

            # Link
            link_el = card.select_one("a[href]")
            product_url = ""
            if link_el and link_el.get("href"):
                product_url = urljoin(url, link_el["href"])

            key = (name.lower(), price)
            if key in seen:
                continue
            seen.add(key)

            rows.append(
                {
                    "name": name[:200],
                    "price": price,
                    "url": product_url,
                    "container": sniff_container(name),
                    "raw_text": price_text[:80],
                }
            )

        return rows
