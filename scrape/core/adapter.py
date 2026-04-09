"""
Adapter base class.

Every supplier-specific scraper subclasses Adapter and implements at least
`start_urls()` — the list of catalog/listing pages to crawl. Override any
other hook to customize behavior. All of the heavy lifting (fetching,
stealth, parsing, vault lookup) lives in the core and is reusable.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable, Optional

from .extractor import extract_prices_from_html
from .fetcher import FetchResult, fetch
from .stealth import BrowserProfile, human_delay
from .vault import Credential, load_vault

log = logging.getLogger("bloombox.adapter")


@dataclass
class ScrapeResult:
    supplier_id: int
    supplier_name: str
    scraped_at: str
    products: list[dict] = field(default_factory=list)
    pages_fetched: int = 0
    tier_used: str = ""
    errors: list[str] = field(default_factory=list)
    login_ok: Optional[bool] = None

    def as_dict(self) -> dict:
        return {
            "supplier_id": self.supplier_id,
            "supplier_name": self.supplier_name,
            "scraped_at": self.scraped_at,
            "products": self.products,
            "pages_fetched": self.pages_fetched,
            "tier_used": self.tier_used,
            "errors": self.errors,
            "login_ok": self.login_ok,
        }


class Adapter:
    # Subclasses MUST override
    supplier_id: int = 0
    supplier_name: str = ""
    requires_login: bool = False

    # Optional overrides
    prefer_tier: str | None = None       # 'curl_cffi' | 'playwright' | 'undetected'
    max_pages: int = 20
    delay_between_pages: str = "page"     # stealth.human_delay kind

    def __init__(self, profile: BrowserProfile | None = None,
                 credential: Credential | None = None):
        self.profile = profile or BrowserProfile.random()
        self.credential = credential
        self.result = ScrapeResult(
            supplier_id=self.supplier_id,
            supplier_name=self.supplier_name,
            scraped_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )

    # --- overrideable hooks -----------------------------------------------
    def start_urls(self) -> list[str]:
        """Return the list of catalog/listing URLs to crawl."""
        raise NotImplementedError

    def login(self) -> bool:
        """Override for login-required sites. Return True on success."""
        return True

    def parse_page(self, html: str, url: str) -> list[dict]:
        """Parse one page. Default delegates to the generic extractor."""
        return extract_prices_from_html(html, url)

    def discover_urls(self, html: str, url: str) -> list[str]:
        """Override to follow pagination or category links."""
        return []

    # --- run loop ---------------------------------------------------------
    def run(self) -> ScrapeResult:
        try:
            if self.requires_login:
                ok = self.login()
                self.result.login_ok = ok
                if not ok:
                    self.result.errors.append("login failed")
                    return self.result

            to_visit: list[str] = list(self.start_urls())
            visited: set[str] = set()

            while to_visit and self.result.pages_fetched < self.max_pages:
                url = to_visit.pop(0)
                if url in visited:
                    continue
                visited.add(url)
                res = self._fetch(url)
                if not res.ok:
                    self.result.errors.append(
                        f"fetch failed {url}: status={res.status} "
                        f"blocked={res.blocked} err={res.error}"
                    )
                    continue

                self.result.tier_used = res.tier
                self.result.pages_fetched += 1

                try:
                    products = self.parse_page(res.html, res.final_url or url)
                    for p in products:
                        p.setdefault("supplier_id", self.supplier_id)
                        p.setdefault("supplier_name", self.supplier_name)
                    self.result.products.extend(products)
                except Exception as e:
                    self.result.errors.append(f"parse error {url}: {e}")

                try:
                    for nxt in self.discover_urls(res.html, res.final_url or url):
                        if nxt not in visited:
                            to_visit.append(nxt)
                except Exception as e:
                    self.result.errors.append(f"discover error {url}: {e}")

                human_delay(self.delay_between_pages)

            return self.result
        except Exception as e:
            log.exception("adapter crash")
            self.result.errors.append(f"adapter crash: {e}")
            return self.result

    # --- internals --------------------------------------------------------
    def _fetch(self, url: str) -> FetchResult:
        return fetch(
            url,
            supplier_id=self.supplier_id,
            profile=self.profile,
            prefer=self.prefer_tier,
        )


# -------------------------------------------------------------------------
# Adapter registry
# -------------------------------------------------------------------------
_REGISTRY: dict[int, type[Adapter]] = {}


def register(cls: type[Adapter]) -> type[Adapter]:
    if not cls.supplier_id:
        raise ValueError(f"{cls.__name__} missing supplier_id")
    _REGISTRY[cls.supplier_id] = cls
    return cls


def get_adapter(supplier_id: int) -> type[Adapter] | None:
    return _REGISTRY.get(supplier_id)


def all_adapters() -> list[type[Adapter]]:
    return list(_REGISTRY.values())


def load_registered_adapters() -> None:
    """Import all adapter modules so their @register decorators fire."""
    import importlib
    import pkgutil
    from .. import adapters as adapters_pkg  # type: ignore

    for _, name, _ in pkgutil.iter_modules(adapters_pkg.__path__):
        if name.startswith("_"):
            continue
        importlib.import_module(f"scrape.adapters.{name}")
