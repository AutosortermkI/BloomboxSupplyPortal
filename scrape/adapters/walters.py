"""
Walters Gardens (id=110) — example login-required adapter.

Shows the pattern for a site that gates prices behind authentication:
1. Force the Playwright tier because we need a stateful browser session.
2. Override `login()` to fill in credentials from the vault.
3. Override `start_urls()` + `discover_urls()` to walk the availability
   catalog after authenticating.

Selectors below are educated guesses — update them when you have an
account and can inspect the real DOM. They're wrapped in try/except so
a schema change downgrades gracefully instead of crashing the run.
"""
from __future__ import annotations

import logging
from typing import Optional

from ..core.adapter import Adapter, register
from ..core.fetcher import FetchResult, _fetch_playwright  # reuse tier directly
from ..core.stealth import human_delay

log = logging.getLogger("bloombox.walters")


@register
class WaltersAdapter(Adapter):
    supplier_id = 110
    supplier_name = "Walters Gardens"
    requires_login = True
    prefer_tier = "playwright"
    max_pages = 30

    LOGIN_URL = "https://www.waltersgardens.com/customer/account/login/"
    CATALOG_URL = "https://www.waltersgardens.com/availability/"

    def start_urls(self) -> list[str]:
        return [self.CATALOG_URL]

    def login(self) -> bool:
        if not self.credential or not self.credential.user:
            log.warning("no credential for walters gardens")
            return False
        # We drive Playwright directly here because login is multi-step.
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
        except Exception as e:
            log.error("playwright unavailable: %s", e)
            return False

        from ..core.stealth import save_cookies
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=[
                    "--disable-blink-features=AutomationControlled",
                ])
                context = browser.new_context(
                    user_agent=self.profile.user_agent,
                    viewport={"width": self.profile.viewport[0],
                              "height": self.profile.viewport[1]},
                    locale=self.profile.locale,
                )
                page = context.new_page()
                page.goto(self.LOGIN_URL, wait_until="domcontentloaded", timeout=45000)
                human_delay("read")

                # Try a few common selectors for the username field
                for sel in ["input[name='login[username]']", "input#email",
                            "input[name='email']", "input[type='email']"]:
                    try:
                        page.fill(sel, self.credential.user, timeout=3000)
                        break
                    except Exception:
                        continue
                human_delay("type")

                for sel in ["input[name='login[password]']", "input#pass",
                            "input[name='password']", "input[type='password']"]:
                    try:
                        page.fill(sel, self.credential.password, timeout=3000)
                        break
                    except Exception:
                        continue
                human_delay("click")

                for sel in ["button[type='submit']", "button.action.login",
                            "button:has-text('Sign In')",
                            "button:has-text('Log In')"]:
                    try:
                        page.click(sel, timeout=3000)
                        break
                    except Exception:
                        continue

                try:
                    page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass

                cookies = context.cookies()
                save_cookies(self.supplier_id,
                             {c["name"]: c["value"] for c in cookies})

                html = page.content().lower()
                success = ("sign out" in html or "logout" in html or
                           "my account" in html) and "invalid" not in html

                context.close()
                browser.close()
                return success
        except Exception as e:
            log.exception("walters login crashed")
            self.result.errors.append(f"login crash: {e}")
            return False

    def discover_urls(self, html: str, url: str) -> list[str]:
        from bs4 import BeautifulSoup  # type: ignore
        from urllib.parse import urljoin
        soup = BeautifulSoup(html, "lxml")
        out: list[str] = []
        for a in soup.select("a[href]"):
            href = a["href"]
            if any(k in href for k in ("/availability/", "/catalog/", "/product/")):
                full = urljoin(url, href)
                out.append(full)
        return list(dict.fromkeys(out))[:20]
