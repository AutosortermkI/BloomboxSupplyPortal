"""
Quality Greenhouses ePIcas wholesale portal — interactive iframe-based system.

The portal loads via guest access at https://epicas.qualitygreenhouses.net and
renders a JS-heavy iframe containing the "Crop Status Availability" data. The
system requires:

1. Following redirects to get a session ID (vSessionId)
2. Switching into the iframe context
3. Iterating through "Form" dropdown categories (ENDCAP ENHANCERS, etc.)
4. Parsing HTML table with columns:
   - Description (name)
   - Container Size
   - Bud & Color
   - Cracking Color
   - Budded
   - Retail Ready
   - Emerging
   - Crop (SKU)
   - Container (code)

Strategy: Use Playwright with direct iframe handling since curl_cffi cannot
execute JS or manage DOM state. Navigate the dropdown menu and parse the
resulting table rows.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from bs4 import BeautifulSoup, Tag  # type: ignore

from ..core.adapter import Adapter, register, ScrapeResult
from ..core.stealth import BrowserProfile

log = logging.getLogger("bloombox.adapter")


@register
class QualityGreenhousesAdapter(Adapter):
    supplier_id = 16
    supplier_name = "Quality Greenhouses"
    requires_login = False
    prefer_tier = "playwright"
    max_pages = 1  # We override run() so this isn't used in standard flow

    def start_urls(self) -> list[str]:
        # Not used — we override run()
        return []

    def run(self) -> ScrapeResult:
        """Override the standard fetch/parse loop to handle interactive iframe."""
        try:
            products = self._scrape_epicas()
            self.result.products = products
            self.result.pages_fetched = 1
            self.result.tier_used = "playwright"
            return self.result
        except Exception as e:
            log.exception("Quality Greenhouses scrape failed")
            self.result.errors.append(f"scrape failed: {e}")
            return self.result

    def _scrape_epicas(self) -> list[dict]:
        """Main scraping logic using Playwright."""
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
        except Exception as e:
            raise RuntimeError(f"playwright not installed: {e}")

        products = []

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--no-sandbox",
                ],
            )
            context = browser.new_context(
                user_agent=self.profile.user_agent,
                viewport={"width": self.profile.viewport[0], "height": self.profile.viewport[1]},
                locale=self.profile.locale,
                timezone_id=self.profile.timezone,
                extra_http_headers={"Accept-Language": self.profile.accept_language},
            )

            # Add stealth scripts
            context.add_init_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
                "window.chrome={runtime:{}};"
                "Object.defineProperty(navigator,'languages',{get:()=>['en-US','en']});"
            )

            page = context.new_page()

            try:
                # Navigate to the guest portal
                log.info("Navigating to ePIcas portal")
                page.goto("https://epicas.qualitygreenhouses.net", timeout=45000, wait_until="domcontentloaded")

                # Wait for session redirect to complete and iframe to load
                page.wait_for_load_state("networkidle", timeout=30000)

                # The main content is in an iframe — get its locator
                iframe_locator = page.frame_locator("iframe#epicasIframe")
                if not iframe_locator:
                    raise RuntimeError("epicasIframe not found")

                frame = iframe_locator

                # Navigate to Availability > Crop Status via menu
                log.info("Navigating to Crop Status Availability")
                self._navigate_to_availability(frame)

                # Get all form categories from dropdown and scrape each
                log.info("Scraping all form categories")
                products.extend(self._scrape_all_forms(frame))

            finally:
                page.close()
                context.close()
                browser.close()

        # Dedupe and add supplier info
        seen = set()
        unique = []
        for p in products:
            key = (p.get("sku", ""), p.get("container", ""))
            if key not in seen:
                seen.add(key)
                p.setdefault("supplier_id", self.supplier_id)
                p.setdefault("supplier_name", self.supplier_name)
                unique.append(p)

        return unique

    def _navigate_to_availability(self, frame) -> None:
        """Click through menu to reach Crop Status Availability."""
        try:
            # The menu structure is: Availability > Crop Status
            # Look for a menu item or link labeled "Availability"
            # This is site-specific; we may need to try multiple selectors

            # Try clicking a menu item or button labeled with "Availability"
            menu_xpath = "//span[contains(text(), 'Availability')] | //a[contains(text(), 'Availability')] | //button[contains(text(), 'Availability')]"
            menu_item = frame.locator(f"xpath={menu_xpath}").first

            if menu_item.is_visible():
                menu_item.click()
                frame.page.wait_for_load_state("networkidle", timeout=15000)

            # Now click "Crop Status" submenu
            crop_status_xpath = "//span[contains(text(), 'Crop Status')] | //a[contains(text(), 'Crop Status')]"
            crop_status = frame.locator(f"xpath={crop_status_xpath}").first

            if crop_status.is_visible():
                crop_status.click()
                frame.page.wait_for_load_state("networkidle", timeout=15000)

        except Exception as e:
            log.warning(f"Menu navigation failed (may already be on page): {e}")

    def _scrape_all_forms(self, frame) -> list[dict]:
        """Iterate through all "Form" dropdown options and scrape each."""
        products = []

        try:
            # Find the form dropdown — it should have options like "ENDCAP ENHANCERS", etc.
            # Look for a select element or dropdown button
            dropdown_selectors = [
                "select[name*='Form' i]",
                "select[id*='Form' i]",
                "select[name*='form' i]",
                "div[class*='Form'i] select",
                "select",
            ]

            dropdown = None
            for selector in dropdown_selectors:
                try:
                    el = frame.locator(selector).first
                    if el.is_visible():
                        dropdown = el
                        break
                except Exception:
                    continue

            if not dropdown:
                log.warning("Form dropdown not found; scraping current page only")
                products.extend(self._parse_availability_table(frame))
                return products

            # Get all option values from the dropdown
            options = frame.locator(f"{dropdown_selectors[0] or 'select'} option").all()
            form_values = [opt.get_attribute("value") for opt in options]
            form_values = [v for v in form_values if v]

            log.info(f"Found {len(form_values)} form categories")

            # Scrape each form
            for i, form_val in enumerate(form_values):
                try:
                    log.info(f"Scraping form {i+1}/{len(form_values)}: {form_val}")

                    # Select the form from dropdown
                    frame.locator(dropdown_selectors[0] or "select").select_option(form_val)
                    frame.page.wait_for_load_state("networkidle", timeout=15000)

                    # Parse the table for this form
                    form_products = self._parse_availability_table(frame)
                    products.extend(form_products)

                except Exception as e:
                    log.warning(f"Failed to scrape form {form_val}: {e}")
                    continue

        except Exception as e:
            log.warning(f"Error iterating forms: {e}")
            # Fall back to scraping current page
            products.extend(self._parse_availability_table(frame))

        return products

    def _parse_availability_table(self, frame) -> list[dict]:
        """Parse the HTML table on the current page."""
        products = []

        try:
            # Get the HTML content of the frame
            html = frame.locator("html").inner_html()
            soup = BeautifulSoup(html, "lxml")

            # Find the main table — it should contain product rows
            # Try multiple table selectors
            table = None
            for selector in ["table", "table[class*='data' i]", "table[class*='availability' i]"]:
                t = soup.select_one(selector)
                if t:
                    table = t
                    break

            if not table:
                log.warning("No table found on current page")
                return products

            # Find all table rows (skip header)
            rows = table.find_all("tr")
            if len(rows) <= 1:
                log.warning("No data rows in table")
                return products

            header_row = rows[0]
            data_rows = rows[1:]

            # Parse header to understand column positions
            headers = [th.get_text(strip=True).lower() for th in header_row.find_all(["th", "td"])]

            # Column indices (adjust based on actual headers found)
            name_idx = self._find_column_index(headers, ["description", "name", "product"])
            size_idx = self._find_column_index(headers, ["container size", "size"])
            bud_idx = self._find_column_index(headers, ["bud & color", "bud"])
            cracking_idx = self._find_column_index(headers, ["cracking color", "cracking"])
            budded_idx = self._find_column_index(headers, ["budded"])
            retail_idx = self._find_column_index(headers, ["retail ready", "retail"])
            emerging_idx = self._find_column_index(headers, ["emerging"])
            sku_idx = self._find_column_index(headers, ["crop", "sku"])
            container_code_idx = self._find_column_index(headers, ["container", "code"])

            # Parse data rows
            for row in data_rows:
                cells = row.find_all("td")
                if len(cells) < 2:
                    continue

                try:
                    # Extract values safely
                    name = cells[name_idx].get_text(strip=True) if name_idx < len(cells) else ""
                    size = cells[size_idx].get_text(strip=True) if size_idx < len(cells) else ""
                    bud_color = cells[bud_idx].get_text(strip=True) if bud_idx < len(cells) else ""
                    cracking = cells[cracking_idx].get_text(strip=True) if cracking_idx < len(cells) else ""
                    budded = self._parse_int(cells[budded_idx].get_text(strip=True) if budded_idx < len(cells) else "0")
                    retail_ready = self._parse_int(cells[retail_idx].get_text(strip=True) if retail_idx < len(cells) else "0")
                    emerging = self._parse_int(cells[emerging_idx].get_text(strip=True) if emerging_idx < len(cells) else "0")
                    sku = cells[sku_idx].get_text(strip=True) if sku_idx < len(cells) else ""
                    container_code = cells[container_code_idx].get_text(strip=True) if container_code_idx < len(cells) else ""

                    if not name or not sku:
                        continue

                    # Total available across all stages
                    total_available = budded + retail_ready + emerging

                    products.append({
                        "name": name[:200],
                        "sku": sku,
                        "container": container_code or size,
                        "container_size": size,
                        "available": total_available,
                        "bud_color": bud_color,
                        "cracking_color": cracking,
                        "budded": budded,
                        "retail_ready": retail_ready,
                        "emerging": emerging,
                        "raw_text": f"epicas:{sku}",
                    })

                except Exception as e:
                    log.debug(f"Failed to parse row: {e}")
                    continue

        except Exception as e:
            log.error(f"Error parsing availability table: {e}")

        return products

    @staticmethod
    def _find_column_index(headers: list[str], keywords: list[str]) -> int:
        """Find the first column matching any of the keywords."""
        for i, header in enumerate(headers):
            for kw in keywords:
                if kw in header:
                    return i
        return 0  # Default to first column if not found

    @staticmethod
    def _parse_int(value: str) -> int:
        """Parse an integer from a string, returning 0 on failure."""
        try:
            # Remove commas and whitespace
            value = value.replace(",", "").strip()
            return int(value) if value else 0
        except (ValueError, TypeError):
            return 0
