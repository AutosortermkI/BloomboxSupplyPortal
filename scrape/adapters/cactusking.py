"""
The Cactus King — Drupal/Ubercart plant catalog.

Products are rendered as `div.node.node-type-plant` blocks. Each block
has a header region with the plant name in an `<a>` tag, and an
optional `div.add-to-cart` form with `label.option` elements containing
size + price (e.g. "5 gallon, $29.99").

The correct domain is thecactusking.com (not cactuskingfl.com).
Category pages paginate via `?page=N`.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup  # type: ignore

from ..core.adapter import Adapter, register
from ..core.extractor import sniff_container

_SIZE_PRICE = re.compile(
    r"([\w\s./-]+?),?\s+\$(\d{1,4}(?:\.\d{1,2})?)", re.IGNORECASE
)


@register
class CactusKingAdapter(Adapter):
    supplier_id = 312
    supplier_name = "Cactus King"
    requires_login = False
    prefer_tier = "curl_cffi"
    max_pages = 12

    def start_urls(self) -> list[str]:
        return [
            "https://thecactusking.com/category/plants/complete-plant-list",
            "https://thecactusking.com/category/plants/flowering-cactus",
            "https://thecactusking.com/category/plants/cactus",
        ]

    def parse_page(self, html: str, url: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        rows: list[dict] = []
        seen: set[tuple[str, float]] = set()

        # Drupal Ubercart: each product is a div.node.node-type-plant
        for node in soup.find_all("div", class_="node-type-plant"):
            # Extract product name from header region link
            header = node.find("div", class_="nd-region-header")
            name = ""
            product_url = ""
            if header:
                a = header.find("a", href=True)
                if a:
                    name = a.get_text(strip=True)
                    product_url = urljoin(url, a["href"])
            if not name or len(name) > 200:
                continue

            # Extract prices from form labels (label.option)
            # Prices are in format: "5 gallon, $29.99"
            found_prices = False
            for label in node.find_all("label", class_="option"):
                text = label.get_text(strip=True)
                m = _SIZE_PRICE.search(text)
                if not m:
                    continue
                size_text = m.group(1).strip()
                try:
                    price = float(m.group(2))
                except ValueError:
                    continue
                if price <= 0 or price > 5000:
                    continue

                full_name = f"{name} ({size_text})"
                key = (full_name.lower(), price)
                if key in seen:
                    continue
                seen.add(key)
                found_prices = True

                rows.append({
                    "name": full_name[:200],
                    "price": price,
                    "url": product_url,
                    "container": sniff_container(size_text) or size_text,
                    "raw_text": text[:80],
                })

        return rows

    def discover_urls(self, html: str, url: str) -> list[str]:
        """Follow Drupal pagination (?page=N)."""
        soup = BeautifulSoup(html, "lxml")
        found: list[str] = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "page=" in href:
                full = urljoin(url, href)
                if full not in found and full != url:
                    found.append(full)
        return found
