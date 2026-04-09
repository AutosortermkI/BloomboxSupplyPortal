"""
Generic public-site adapters.

For suppliers whose prices are visible on a public catalog page, we can
register a one-line adapter that points at the start URL(s). The generic
extractor handles the rest (JSON-LD / product cards / regex fallback).

Add more here as you verify each supplier loads cleanly.
"""
from __future__ import annotations

from ..core.adapter import Adapter, register


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


# ---- PUBLIC-PRICING SUPPLIERS ----
# Start with a curated list of suppliers known to show prices without login.

_simple(207, "SiteOne Landscape Supply",
        ["https://www.siteone.com/en/catalog/category/nursery/",
         "https://www.siteone.com/en/catalog/category/plants/"],
        tier="playwright")

_simple(178, "Van Engelen Bulbs",
        ["https://www.vanengelen.com/catalog/"],
        tier="curl_cffi")

_simple(179, "Colorblends Bulbs",
        ["https://www.colorblends.com/shop/",
         "https://www.colorblends.com/shop/tulips/",
         "https://www.colorblends.com/shop/daffodils/"],
        tier="curl_cffi")

_simple(210, "Arbico Organics",
        ["https://www.arbico-organics.com/category/organic-pest-control",
         "https://www.arbico-organics.com/category/plants-seeds"],
        tier="curl_cffi")

_simple(211, "Organic Mechanics Soil",
        ["https://organicmechanicsoil.com/shop/"],
        tier="curl_cffi")

_simple(61,  "DV Flora",
        ["https://dvflora.com/shop/"],
        tier="playwright")

_simple(52,  "Riggins Nursery",
        ["https://www.riggins-nursery.com/complete-availability-prices"],
        tier="curl_cffi")

_simple(59,  "Lucas Greenhouses",
        ["https://www.lucasgreenhouses.com/page/Availability-Price-List"],
        tier="curl_cffi")

_simple(129, "Schroeder Gardens",
        ["https://www.schroedergardens.com/shop"],
        tier="curl_cffi")

_simple(23,  "Creek Hill Nursery",
        ["https://www.creekhillnursery.com/index.php/availability"],
        tier="curl_cffi")

_simple(27,  "Miller Plant Farm",
        ["https://millerplantfarm.com/wholesale"],
        tier="curl_cffi")

_simple(36,  "Clear Ridge Nursery",
        ["https://www.clearridgenursery.com/products/wholesale/"],
        tier="curl_cffi")

_simple(202, "HC Companies",
        ["https://hc-companies.com/plant-pots/"],
        tier="curl_cffi")
