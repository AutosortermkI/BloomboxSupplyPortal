"""
Stealth / human-mimicking helpers.

Centralizes every anti-detection behavior so adapters don't reinvent:
- Rotating realistic User-Agents
- Randomized viewport + language + timezone
- Human-like delays (with jitter + per-action type)
- Session/cookie persistence to disk
- Optional proxy rotation
"""
from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# A small set of real, current desktop Chrome UAs. fake-useragent is an
# optional enrichment at runtime; this list guarantees sane defaults if it
# isn't installed or its cache is unavailable.
_DEFAULT_UAS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

_VIEWPORTS = [
    (1920, 1080), (1680, 1050), (1536, 864), (1440, 900), (1366, 768),
]

_LOCALES = ["en-US", "en-GB", "en-CA"]
_TIMEZONES = ["America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles"]


@dataclass
class BrowserProfile:
    """A synthesized-but-consistent identity for one scrape session."""
    user_agent: str
    viewport: tuple[int, int]
    locale: str
    timezone: str
    accept_language: str

    @classmethod
    def random(cls) -> "BrowserProfile":
        # Use our hardcoded UA list — reliable and avoids fake-useragent's
        # noisy fallback warnings that clutter logs on every invocation.
        ua = random.choice(_DEFAULT_UAS)
        locale = random.choice(_LOCALES)
        return cls(
            user_agent=ua,
            viewport=random.choice(_VIEWPORTS),
            locale=locale,
            timezone=random.choice(_TIMEZONES),
            accept_language=f"{locale},{locale.split('-')[0]};q=0.9",
        )

    def as_headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": self.accept_language,
            "Accept-Encoding": "gzip, deflate, br",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }


def human_delay(kind: str = "page") -> None:
    """Sleep for a random, type-appropriate duration.

    kind:
      'page'  — between page navigations (1.5-4.5s)
      'click' — after a click (0.4-1.2s)
      'type'  — between typed characters (0.05-0.18s)
      'read'  — simulates reading a page (2.0-6.0s)
      'micro' — quick pause (0.1-0.3s)
    """
    ranges = {
        "page":  (1.5, 4.5),
        "click": (0.4, 1.2),
        "type":  (0.05, 0.18),
        "read":  (2.0, 6.0),
        "micro": (0.1, 0.3),
    }
    lo, hi = ranges.get(kind, (1.0, 2.0))
    time.sleep(random.uniform(lo, hi))


# -------------------------------------------------------------------------
# Session / cookie persistence
# -------------------------------------------------------------------------
_STATE_DIR = Path(__file__).resolve().parents[1] / "cache" / "sessions"
_STATE_DIR.mkdir(parents=True, exist_ok=True)


def session_path(supplier_id: int | str) -> Path:
    return _STATE_DIR / f"supplier_{supplier_id}.json"


def load_cookies(supplier_id: int | str) -> dict[str, str]:
    p = session_path(supplier_id)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text()).get("cookies", {})
    except Exception:
        return {}


def save_cookies(supplier_id: int | str, cookies: dict[str, str]) -> None:
    p = session_path(supplier_id)
    existing = {}
    if p.exists():
        try:
            existing = json.loads(p.read_text())
        except Exception:
            pass
    existing["cookies"] = cookies
    existing["updated_at"] = time.time()
    p.write_text(json.dumps(existing, indent=2))


# -------------------------------------------------------------------------
# Proxy rotation (optional — reads BLOOMBOX_PROXIES env var)
# -------------------------------------------------------------------------
def get_proxy() -> Optional[str]:
    """Return one proxy from the pool (comma-separated env var) or None."""
    pool = os.environ.get("BLOOMBOX_PROXIES", "").strip()
    if not pool:
        return None
    proxies = [p.strip() for p in pool.split(",") if p.strip()]
    return random.choice(proxies) if proxies else None
