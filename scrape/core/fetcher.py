"""
Three-tier fetcher cascade.

Tier 1: curl_cffi — impersonates a real Chrome TLS/JA3 fingerprint. Beats
         Cloudflare/Akamai/DataDome on a surprising number of sites while
         staying a lightweight HTTP client.
Tier 2: Playwright + stealth — real headless Chromium with human-like
         behavior. Handles JS-rendered content and basic bot checks.
Tier 3: undetected-chromedriver — Selenium-based, patched Chrome binary.
         Nuclear option for the most hardened anti-bot sites.

Callers use `fetch(url, ...)` and get back a FetchResult. The cascade
auto-escalates when a tier returns suspicious content (captcha, 403, empty
body, known block pages). You can also force a tier via `prefer=`.
"""
from __future__ import annotations

import logging
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from .stealth import BrowserProfile, get_proxy, human_delay, load_cookies, save_cookies

log = logging.getLogger("bloombox.fetcher")

# Signals that a response is probably a block page even if status == 200.
# Be specific to avoid false positives on normal pages that mention "access"
# or "captcha" as regular text (e.g. Lucas Greenhouses availability page).
_BLOCK_PATTERNS = [
    re.compile(r"cf-browser-verification|checking your browser|just a moment.*cloudflare", re.I),
    re.compile(r"<title>\s*(access denied|403 forbidden|request blocked|blocked)\s*</title>", re.I),
    re.compile(r"unusual traffic from your (computer|network)", re.I),
    re.compile(r"recaptcha|hcaptcha|g-recaptcha|captcha.{0,30}(challenge|verify|solve|required)", re.I),
    re.compile(r"enable javascript and cookies to continue", re.I),
    re.compile(r"datadome|perimeterx|incapsula|imperva", re.I),
]


@dataclass
class FetchResult:
    url: str
    status: int
    html: str
    tier: str  # "curl_cffi" | "playwright" | "undetected"
    cookies: dict[str, str] = field(default_factory=dict)
    final_url: Optional[str] = None
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.status == 200 and not self.blocked

    @property
    def blocked(self) -> bool:
        if not self.html:
            return True
        sample = self.html[:4000].lower()
        return any(p.search(sample) for p in _BLOCK_PATTERNS)


# -------------------------------------------------------------------------
# Tier 1: curl_cffi
# -------------------------------------------------------------------------
def _fetch_curl_cffi(url: str, profile: BrowserProfile, supplier_id: int | str | None,
                    timeout: int = 30) -> FetchResult:
    try:
        from curl_cffi import requests as cc_requests  # type: ignore
    except Exception as e:
        return FetchResult(url, 0, "", "curl_cffi", error=f"curl_cffi not installed: {e}")

    cookies = load_cookies(supplier_id) if supplier_id is not None else {}
    proxy = get_proxy()
    proxies = {"http": proxy, "https": proxy} if proxy else None

    try:
        # impersonate cycles through recent Chrome versions curl_cffi supports
        impersonate = random.choice(["chrome124", "chrome120", "chrome116", "safari17_0"])
        r = cc_requests.get(
            url,
            headers=profile.as_headers(),
            cookies=cookies,
            proxies=proxies,
            timeout=timeout,
            impersonate=impersonate,
            allow_redirects=True,
        )
        if supplier_id is not None:
            try:
                save_cookies(supplier_id, {k: v for k, v in r.cookies.items()})
            except Exception:
                pass
        return FetchResult(
            url=url,
            status=r.status_code,
            html=r.text or "",
            tier="curl_cffi",
            cookies={k: v for k, v in r.cookies.items()},
            final_url=str(r.url),
        )
    except Exception as e:
        return FetchResult(url, 0, "", "curl_cffi", error=str(e))


# -------------------------------------------------------------------------
# Tier 2: Playwright + stealth
# -------------------------------------------------------------------------
def _fetch_playwright(url: str, profile: BrowserProfile, supplier_id: int | str | None,
                     timeout: int = 45, wait_for: str | None = None) -> FetchResult:
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as e:
        return FetchResult(url, 0, "", "playwright", error=f"playwright not installed: {e}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-site-isolation-trials",
                    "--no-sandbox",
                ],
            )
            context = browser.new_context(
                user_agent=profile.user_agent,
                viewport={"width": profile.viewport[0], "height": profile.viewport[1]},
                locale=profile.locale,
                timezone_id=profile.timezone,
                extra_http_headers={"Accept-Language": profile.accept_language},
            )
            # Strip the webdriver flag that most bot detectors check
            context.add_init_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
                "window.chrome={runtime:{}};"
                "Object.defineProperty(navigator,'languages',{get:()=>['en-US','en']});"
                "Object.defineProperty(navigator,'plugins',{get:()=>[1,2,3,4,5]});"
            )
            # Restore cookies for this supplier
            if supplier_id is not None:
                cookies = load_cookies(supplier_id)
                if cookies:
                    try:
                        context.add_cookies([
                            {"name": k, "value": v, "url": url}
                            for k, v in cookies.items()
                        ])
                    except Exception:
                        pass
            page = context.new_page()
            try:
                from playwright_stealth import stealth_sync  # type: ignore
                stealth_sync(page)
            except Exception:
                pass

            response = page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")

            # If a wait_for selector was given, wait for it to appear
            # (critical for Wix/React sites that render client-side)
            if wait_for:
                try:
                    page.wait_for_selector(wait_for, timeout=15_000)
                except Exception:
                    log.warning("wait_for selector %r not found, continuing", wait_for)

            # Let JS settle and pretend we're reading
            human_delay("read")
            try:
                # Simulate a scroll — many sites only render prices on scroll
                page.mouse.wheel(0, random.randint(400, 900))
                human_delay("click")
                page.mouse.wheel(0, random.randint(400, 900))
            except Exception:
                pass

            html = page.content()
            status = response.status if response else 0
            final_url = page.url

            # Persist cookies
            if supplier_id is not None:
                try:
                    pw_cookies = context.cookies()
                    save_cookies(
                        supplier_id,
                        {c["name"]: c["value"] for c in pw_cookies},
                    )
                except Exception:
                    pass

            context.close()
            browser.close()
            return FetchResult(url, status, html, "playwright", final_url=final_url)
    except Exception as e:
        return FetchResult(url, 0, "", "playwright", error=str(e))


# -------------------------------------------------------------------------
# Tier 3: undetected-chromedriver
# -------------------------------------------------------------------------
def _detect_chrome_major() -> int | None:
    """Auto-detect the installed Chrome/Chromium major version."""
    import shutil, subprocess
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        path = shutil.which(name)
        if path:
            try:
                out = subprocess.check_output([path, "--version"], timeout=5, text=True)
                # e.g. "Google Chrome 146.0.7680.178"
                m = re.search(r"(\d+)\.", out)
                if m:
                    return int(m.group(1))
            except Exception:
                continue
    # macOS: Chrome lives in /Applications
    mac_chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    if mac_chrome.exists():
        try:
            import subprocess
            out = subprocess.check_output([str(mac_chrome), "--version"], timeout=5, text=True)
            m = re.search(r"(\d+)\.", out)
            if m:
                return int(m.group(1))
        except Exception:
            pass
    return None


def _fetch_undetected(url: str, profile: BrowserProfile, supplier_id: int | str | None,
                     timeout: int = 60) -> FetchResult:
    try:
        import undetected_chromedriver as uc  # type: ignore
        from selenium.webdriver.support.ui import WebDriverWait  # type: ignore
    except Exception as e:
        return FetchResult(url, 0, "", "undetected", error=f"undetected-chromedriver not installed: {e}")

    driver = None
    try:
        options = uc.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument(f"--user-agent={profile.user_agent}")
        options.add_argument(f"--window-size={profile.viewport[0]},{profile.viewport[1]}")
        options.add_argument(f"--lang={profile.locale}")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        # Auto-detect Chrome version to avoid chromedriver mismatch
        chrome_major = _detect_chrome_major()
        uc_kwargs: dict[str, Any] = {"options": options, "use_subprocess": True}
        if chrome_major:
            uc_kwargs["version_main"] = chrome_major
            log.info("detected Chrome %d — pinning chromedriver", chrome_major)

        driver = uc.Chrome(**uc_kwargs)
        driver.set_page_load_timeout(timeout)
        driver.get(url)
        human_delay("read")
        # Scroll
        driver.execute_script(f"window.scrollTo(0,{random.randint(400,1000)});")
        human_delay("click")
        driver.execute_script(f"window.scrollTo(0,{random.randint(800,2000)});")
        human_delay("click")

        html = driver.page_source
        final_url = driver.current_url
        cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
        if supplier_id is not None:
            save_cookies(supplier_id, cookies)

        return FetchResult(url, 200, html, "undetected",
                           cookies=cookies, final_url=final_url)
    except Exception as e:
        return FetchResult(url, 0, "", "undetected", error=str(e))
    finally:
        try:
            if driver is not None:
                driver.quit()
        except Exception:
            pass


# -------------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------------
TIERS: dict[str, Callable[..., FetchResult]] = {
    "curl_cffi":  _fetch_curl_cffi,
    "playwright": _fetch_playwright,
    "undetected": _fetch_undetected,
}


def fetch(
    url: str,
    *,
    supplier_id: int | str | None = None,
    profile: BrowserProfile | None = None,
    prefer: str | None = None,
    max_tiers: int = 3,
    wait_for: str | None = None,
) -> FetchResult:
    """Fetch a URL through the cascade, escalating on block.

    - If `prefer` is set, start at that tier (still escalates on failure).
    - `wait_for`: CSS selector to wait for before grabbing HTML (Playwright
      only — ignored by curl_cffi and undetected). Critical for Wix/React
      sites that render product cards client-side.
    - Returns the first FetchResult where `ok` is True, or the last attempt.
    """
    profile = profile or BrowserProfile.random()
    order = ["curl_cffi", "playwright", "undetected"]
    if prefer:
        if prefer not in order:
            raise ValueError(f"unknown tier: {prefer}")
        idx = order.index(prefer)
        order = order[idx:] + order[:idx]  # rotate so preferred is first
    order = order[:max_tiers]

    last: FetchResult | None = None
    for tier in order:
        log.info("fetching %s via %s", url, tier)
        # Pass wait_for to Playwright tier; other tiers ignore the kwarg
        if tier == "playwright":
            result = TIERS[tier](url, profile, supplier_id, wait_for=wait_for)
        else:
            result = TIERS[tier](url, profile, supplier_id)
        last = result
        if result.ok:
            return result
        log.warning("tier %s failed for %s (status=%s blocked=%s err=%s)",
                    tier, url, result.status, result.blocked, result.error)
        human_delay("page")  # cool-down before escalating

    assert last is not None
    return last
