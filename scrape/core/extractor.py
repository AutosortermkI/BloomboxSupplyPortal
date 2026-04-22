"""
Generic price extraction helpers.

`extract_prices_from_html(html)` returns a list of ProductRow dicts suitable
for writing to prices.json. It works on three levels:

1. JSON-LD Product schema — the cleanest, most stable source when present.
2. Common HTML patterns — Shopify/WooCommerce/BigCommerce markup, generic
   "product card" layouts with price + title siblings.
3. Regex fallback — dollar amounts next to plant-sounding nouns, used only
   when the structured passes yield nothing.

Adapters can (and should) override with site-specific selectors, but this
file handles the 80% case with zero configuration.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict, field
from typing import Iterable, Optional

from bs4 import BeautifulSoup  # type: ignore

try:
    from price_parser import Price  # type: ignore
except Exception:
    Price = None  # type: ignore


@dataclass
class ProductRow:
    name: str
    price: float
    unit: str = ""        # e.g. "each", "tray", "50-count"
    container: str = ""   # e.g. "#1", "4.5-inch", "LP50 plug"
    category: str = ""    # free-text category hint
    url: str = ""
    sku: str = ""
    in_stock: Optional[bool] = None
    currency: str = "USD"
    raw_text: str = ""    # keep a small snippet for debugging
    extras: dict = field(default_factory=dict)


# -------------------------------------------------------------------------
# Price parsing primitives
# -------------------------------------------------------------------------
_PRICE_RE = re.compile(r"\$\s?(\d{1,4}(?:,\d{3})*(?:\.\d{1,2})?)")


def parse_price(text: str) -> Optional[float]:
    """Extract a dollar price from text.

    Requires a ``$`` sign to avoid false positives (e.g. "3 gal Container"
    being read as $3.00).  price_parser is used only when a ``$`` is present.
    """
    if not text or "$" not in text:
        return None
    # Regex first — most reliable since it anchors on $
    m = _PRICE_RE.search(text)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except Exception:
            pass
    # price_parser as fallback (but only when $ was already found)
    if Price is not None:
        try:
            p = Price.fromstring(text)
            if p.amount is not None and p.currency == "$":
                return float(p.amount)
        except Exception:
            pass
    return None


# -------------------------------------------------------------------------
# Container / unit sniffing
# -------------------------------------------------------------------------
_CONTAINER_RE = re.compile(
    r"\b("
    r"#\d{1,2}|"                    # #1, #3, #7, #15
    r"\d{1,2}[-\s]*gal(?:lon)?s?|"      # 1-gal, 3 gal, 3-gal
    r"\d{1,2}[\"']?\s*(?:pot|liner|plug|tray)|"
    r"\d{1,2}\.\d{1,2}[\"']?\s*(?:pot|liner|plug)|"
    r"LP\s*\d{1,3}|"
    r"\d{2,4}[- ]?cell|"
    r"\d{1,2}[\"'] container"
    r")",
    re.IGNORECASE,
)


def sniff_container(text: str) -> str:
    if not text:
        return ""
    m = _CONTAINER_RE.search(text)
    return m.group(1).strip() if m else ""


# -------------------------------------------------------------------------
# Pass 1: JSON-LD
# -------------------------------------------------------------------------
def _extract_jsonld(soup: BeautifulSoup, page_url: str) -> list[ProductRow]:
    out: list[ProductRow] = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            blob = json.loads(tag.string or "{}")
        except Exception:
            continue
        objs = blob if isinstance(blob, list) else [blob]
        # JSON-LD can also nest @graph
        nested = []
        for o in objs:
            if isinstance(o, dict) and "@graph" in o:
                nested.extend(o["@graph"])
        objs.extend(nested)
        for o in objs:
            if not isinstance(o, dict):
                continue
            ty = o.get("@type")
            types = ty if isinstance(ty, list) else [ty]
            if "Product" not in types:
                continue
            name = o.get("name", "") or ""
            offers = o.get("offers") or {}
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            price_val = offers.get("price") or offers.get("lowPrice")
            price = parse_price(str(price_val)) if price_val else None
            if price is None:
                continue
            sku = o.get("sku", "") or ""
            currency = (offers.get("priceCurrency") or "USD")
            availability = (offers.get("availability") or "").lower()
            in_stock = "instock" in availability if availability else None
            out.append(ProductRow(
                name=name,
                price=price,
                sku=str(sku),
                currency=currency,
                in_stock=in_stock,
                url=o.get("url") or page_url,
                container=sniff_container(name),
                raw_text="jsonld",
            ))
    return out


# -------------------------------------------------------------------------
# Pass 2: HTML product cards
# -------------------------------------------------------------------------
_CARD_SELECTORS = [
    # Standard e-commerce
    ".product-card", ".product-item", ".product", "li.product",
    ".woocommerce-LoopProduct-link", ".grid-product", ".product-grid-item",
    "article.product", "[data-product-id]",
    # Wix / React (Schroeder Gardens, etc.)
    "[data-hook='product-item-root']",
    # Shopify
    ".product-grid-item", ".grid__item",
    # BigCommerce
    ".productGrid .product", ".card",
]
_NAME_SELECTORS = [
    ".product-title", ".product-name",
    "[data-hook='product-item-product-details']",  # Wix
    "h2.woocommerce-loop-product__title",          # WooCommerce
    "h2", "h3", "a",
]
_PRICE_SELECTORS = [
    ".price", ".product-price", ".money", ".amount",
    "span.price", ".price__regular", "[itemprop='price']",
    "[data-hook='sr-product-item-price-to-pay']",  # Wix
    "span.woocommerce-Price-amount",               # WooCommerce
]


def _first_text(node, selectors: Iterable[str]) -> str:
    for sel in selectors:
        el = node.select_one(sel)
        if el:
            txt = el.get_text(" ", strip=True)
            if txt:
                return txt
    return ""


def _extract_cards(soup: BeautifulSoup, page_url: str) -> list[ProductRow]:
    out: list[ProductRow] = []
    seen_names: set[str] = set()
    for sel in _CARD_SELECTORS:
        for card in soup.select(sel):
            name = _first_text(card, _NAME_SELECTORS)
            if not name or len(name) > 200:
                continue
            price_txt = _first_text(card, _PRICE_SELECTORS)
            price = parse_price(price_txt)
            if price is None:
                continue
            key = (name.lower(), price)
            if key in seen_names:  # dedupe
                continue
            seen_names.add(key)
            link = card.find("a", href=True)
            url = link["href"] if link else page_url
            if url and not url.startswith("http"):
                from urllib.parse import urljoin
                url = urljoin(page_url, url)
            out.append(ProductRow(
                name=name[:200],
                price=price,
                url=url,
                container=sniff_container(name),
                raw_text=price_txt[:120],
            ))
    return out


# -------------------------------------------------------------------------
# Pass 3: regex fallback
# -------------------------------------------------------------------------
_PLANT_NOUNS = re.compile(
    r"\b(perennial|shrub|tree|plug|liner|grass|fern|native|annual|"
    r"hydrangea|hosta|echinacea|rudbeckia|juniper|boxwood|coneflower|"
    r"sedum|daylily|hellebore|heuchera|panicum|tropical|palm|mulch|"
    r"soil|potting|fertilizer|container|pot)\b",
    re.IGNORECASE,
)


def _extract_regex(text: str, page_url: str) -> list[ProductRow]:
    out: list[ProductRow] = []
    # Scan line by line, keep lines that mention a plant noun AND a dollar price
    for line in text.splitlines():
        line = line.strip()
        if not line or len(line) > 300:
            continue
        if not _PLANT_NOUNS.search(line):
            continue
        price = parse_price(line)
        if price is None or price <= 0 or price > 5000:
            continue
        out.append(ProductRow(
            name=_PLANT_NOUNS.sub(lambda m: m.group(0), line)[:180],
            price=price,
            url=page_url,
            container=sniff_container(line),
            raw_text="regex",
        ))
    return out


# -------------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------------
def extract_prices_from_html(html: str, page_url: str = "") -> list[dict]:
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")

    rows: list[ProductRow] = []
    rows += _extract_jsonld(soup, page_url)
    rows += _extract_cards(soup, page_url)
    if not rows:
        rows += _extract_regex(soup.get_text("\n"), page_url)

    # Dedupe by (name_lower, price)
    seen: set[tuple[str, float]] = set()
    deduped: list[ProductRow] = []
    for r in rows:
        key = (r.name.strip().lower(), round(r.price, 2))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)

    return [asdict(r) for r in deduped]
