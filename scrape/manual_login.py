"""Manual headed-browser login handoff for credentialed suppliers.

This module deliberately does not automate CAPTCHA interaction. It can prefill
known login fields, wait for the human to complete any challenge and submit the
form, then persist Playwright storage state for future scraper runs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from .core.stealth import BrowserProfile, storage_state_path
from .core.vault import Credential

USERNAME_SELECTORS = [
    "input[name='username']",
    "input[type='email']",
    "input[name='email']",
    "input#username",
    "input#email",
    "input[type='text']",
]

PASSWORD_SELECTORS = [
    "input[name='password']",
    "input[type='password']",
    "input#password",
    "input#pass",
]

BLOCK_MARKERS = {
    "recaptcha": ("recaptcha", "g-recaptcha", "hcaptcha", "captcha"),
    "invalid": ("invalid password", "invalid username", "incorrect", "login failed"),
}

DEFAULT_SUCCESS_TEXTS = [
    "log out",
    "logout",
    "account details",
    "edit your password and account details",
]
DEFAULT_SUCCESS_URL_PARTS: list[str] = []


@dataclass
class ManualLoginResult:
    supplier_id: int
    login_url: str
    current_url: str
    storage_state_path: str
    success: bool
    reasons: list[str]


def evaluate_login_success(
    html: str,
    url: str,
    *,
    success_texts: Iterable[str] | None = None,
    success_url_contains: Iterable[str] | None = None,
) -> tuple[bool, list[str]]:
    text = (html or "").lower()
    current_url = (url or "").lower()
    reasons: list[str] = []

    for label, markers in BLOCK_MARKERS.items():
        if any(marker in text for marker in markers):
            reasons.append(f"blocked:{label}")

    text_markers = [s.lower() for s in (success_texts or DEFAULT_SUCCESS_TEXTS) if s]
    url_markers = [
        s.lower() for s in (success_url_contains or DEFAULT_SUCCESS_URL_PARTS) if s
    ]
    for marker in text_markers:
        if marker in text:
            reasons.append(f"text:{marker}")
    for marker in url_markers:
        if marker in current_url:
            reasons.append(f"url:{marker}")

    has_success = any(reason.startswith(("text:", "url:")) for reason in reasons)
    if "blocked:invalid" in reasons:
        return False, reasons
    if "blocked:recaptcha" in reasons and not has_success:
        return False, reasons
    return has_success, reasons


def _fill_first(page, selectors: list[str], value: str) -> str:
    for selector in selectors:
        try:
            page.fill(selector, value, timeout=3000)
            return selector
        except Exception:
            continue
    return ""


def prefill_login_fields(page, credential: Credential) -> dict[str, str]:
    """Fill username/password fields when present; never submits the form."""
    username_selector = _fill_first(page, USERNAME_SELECTORS, credential.user)
    password_selector = _fill_first(page, PASSWORD_SELECTORS, credential.password)
    return {
        "username_selector": username_selector,
        "password_selector": password_selector,
    }


def _new_context(browser, profile: BrowserProfile, supplier_id: int):
    state_path = storage_state_path(supplier_id)
    options = {
        "user_agent": profile.user_agent,
        "viewport": {"width": profile.viewport[0], "height": profile.viewport[1]},
        "locale": profile.locale,
        "timezone_id": profile.timezone,
        "extra_http_headers": {"Accept-Language": profile.accept_language},
    }
    if state_path.exists():
        options["storage_state"] = str(state_path)
    return browser.new_context(**options)


def capture_manual_login_session(
    *,
    supplier_id: int,
    credential: Credential,
    login_url: str,
    success_texts: Iterable[str] | None = None,
    success_url_contains: Iterable[str] | None = None,
    timeout_seconds: int = 600,
    headed: bool = True,
    input_func: Callable[[str], str] = input,
    output_func: Callable[[str], None] = print,
) -> ManualLoginResult:
    if not credential.user or not credential.password:
        raise ValueError("credential must include username and password")
    if not login_url:
        raise ValueError("login_url is required")

    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as exc:
        raise RuntimeError(f"playwright not installed: {exc}") from exc

    profile = BrowserProfile.random()
    state_path = storage_state_path(supplier_id)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not headed,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = _new_context(browser, profile, supplier_id)
        context.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
            "window.chrome={runtime:{}};"
            "Object.defineProperty(navigator,'languages',{get:()=>['en-US','en']});"
            "Object.defineProperty(navigator,'plugins',{get:()=>[1,2,3,4,5]});"
        )
        page = context.new_page()
        page.goto(login_url, wait_until="domcontentloaded", timeout=timeout_seconds * 1000)
        prefill_login_fields(page, credential)

        output_func(
            "Complete the supplier login manually in the opened browser. "
            "Do not paste secrets into this terminal. Press Enter here after "
            "the page shows the logged-in account view, or type q to cancel."
        )

        while True:
            response = input_func("Manual login complete? [Enter/q] ").strip().lower()
            if response in {"q", "quit", "cancel"}:
                current_url = page.url
                context.close()
                browser.close()
                return ManualLoginResult(
                    supplier_id=supplier_id,
                    login_url=login_url,
                    current_url=current_url,
                    storage_state_path=str(state_path),
                    success=False,
                    reasons=["cancelled"],
                )

            html = page.content()
            current_url = page.url
            success, reasons = evaluate_login_success(
                html,
                current_url,
                success_texts=success_texts,
                success_url_contains=success_url_contains,
            )
            if success:
                context.storage_state(path=str(state_path))
                context.close()
                browser.close()
                return ManualLoginResult(
                    supplier_id=supplier_id,
                    login_url=login_url,
                    current_url=current_url,
                    storage_state_path=str(state_path),
                    success=True,
                    reasons=reasons,
                )

            output_func(
                "Login success was not detected yet. Leave the browser open, "
                "finish the login flow, then press Enter again; type q to cancel. "
                f"Signals: {', '.join(reasons) if reasons else 'none'}"
            )
