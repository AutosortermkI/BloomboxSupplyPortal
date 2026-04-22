"""
SiteOne Landscape Supply — custom parser.

SiteOne uses a two-level HTML structure:
  Parent (`div.list-plp`): product name, SKU, URL
  Child (`div.variant-item`): price, UOM, stock qty in hidden <input> fields

Prices live in `<input name="product.price.value" value="30.08">` — NOT
in visible text — which is why the generic extractor finds nothing.

Only the undetected-chromedriver tier gets through SiteOne's bot detection.
curl_cffi and Playwright both hit ERR_HTTP2_PROTOCOL_ERROR.
"""
from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag  # type: ignore

from ..core.adapter import Adapter, register
from ..core.extractor import sniff_container


@register
class SiteOneAdapter(Adapter):
    supplier_id = 207
    supplier_name = "SiteOne Landscape Supply"
    requires_login = False
    prefer_tier = "undetected"
    max_pages = 6  # 2 search terms × 3 pages each

    def start_urls(self) -> list[str]:
        return [
            "https://www.siteone.com/en/search?q=perennials&category=Plants",
            "https://www.siteone.com/en/search?q=shrubs&category=Plants",
        ]

    def parse_page(self, html: str, url: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        rows: list[dict] = []
        seen: set[str] = set()

        for parent in soup.find_all("div", class_="list-plp"):
            if not isinstance(parent, Tag):
                continue
            try:
                # SKU from hidden input
                sku_el = parent.find("input", class_="productCodePLP")
                sku = sku_el["value"] if sku_el else ""

                # Product name from anchor > span
                name_el = parent.find("a", class_="name")
                name = ""
                if name_el:
                    span = name_el.find("span")
                    if span:
                        name = " ".join(span.get_text().split())
                if not name:
                    continue

                # Product URL
                product_url = ""
                if name_el and name_el.get("href"):
                    product_url = urljoin("https://www.siteone.com", name_el["href"])

                # Find variant child for price/UOM/stock
                variant = parent.find("div", class_="variant-item")
                if not variant:
                    continue

                # Price from hidden input
                price_el = variant.find("input", attrs={"name": "product.price.value"})
                if not price_el or not price_el.get("value"):
                    continue
                try:
                    price = float(price_el["value"])
                except (ValueError, TypeError):
                    continue
                if price <= 0 or price > 10_000:
                    continue

                # Unit of measure
                uom_el = variant.find("input", attrs={"name": "sellableUom.measure"})
                unit = uom_el["value"] if uom_el and uom_el.get("value") else "Each"

                # Stock quantity
                stock_el = variant.find(
                    "input",
                    attrs={"id": lambda x: x and "plp-availableQty" in x},
                )
                in_stock = None
                if stock_el and stock_el.get("value"):
                    try:
                        in_stock = int(stock_el["value"]) > 0
                    except (ValueError, TypeError):
                        pass

                # Dedupe by SKU
                if sku in seen:
                    continue
                seen.add(sku)

                rows.append({
                    "name": name[:200],
                    "price": price,
                    "unit": unit,
                    "sku": sku,
                    "url": product_url,
                    "in_stock": in_stock,
                    "container": sniff_container(name),
                    "raw_text": f"input[value={price_el['value']}]",
                })
            except Exception:
                continue

        return rows

    def discover_urls(self, html: str, url: str) -> list[str]:
        """Follow SiteOne pagination (Next button)."""
        soup = BeautifulSoup(html, "lxml")
        found: list[str] = []
        # SiteOne uses <a class="page-link" ...> for pagination
        for a in soup.find_all("a", class_="page-link"):
            href = a.get("href", "")
            if href and "page=" in href:
                full = urljoin("https://www.siteone.com", href)
                if full not in found:
                    found.append(full)
        return found
