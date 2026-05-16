import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scrape import manual_login
from scrape.core import fetcher, stealth
from scrape.core.vault import Credential


class ManualLoginSessionTests(unittest.TestCase):
    def test_storage_state_path_uses_supplier_session_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch("scrape.core.stealth._STATE_DIR", Path(tmpdir)):
                path = stealth.storage_state_path(43)

                self.assertEqual(Path(tmpdir) / "supplier_43.storage_state.json", path)
                self.assertFalse(stealth.has_storage_state(43))

                path.write_text(json.dumps({"cookies": []}))
                self.assertTrue(stealth.has_storage_state(43))

    def test_evaluate_login_success_accepts_success_text_or_url(self):
        ok, reasons = manual_login.evaluate_login_success(
            "<html><body>Welcome to My Account</body></html>",
            "https://www.americannativeplants.com/my-account/",
            success_texts=["my account"],
            success_url_contains=["my-account"],
        )

        self.assertTrue(ok)
        self.assertIn("text:my account", reasons)
        self.assertIn("url:my-account", reasons)

    def test_evaluate_login_success_rejects_challenge_or_invalid_login(self):
        ok, reasons = manual_login.evaluate_login_success(
            "<html><body>reCAPTCHA required; invalid password</body></html>",
            "https://www.americannativeplants.com/my-account/",
            success_texts=["my account"],
            success_url_contains=["my-account"],
        )

        self.assertFalse(ok)
        self.assertIn("blocked:recaptcha", reasons)
        self.assertIn("blocked:invalid", reasons)

    def test_default_success_detection_does_not_accept_woocommerce_login_page(self):
        ok, reasons = manual_login.evaluate_login_success(
            "<html><body><h1>My account</h1><form class='woocommerce-form-login'></form></body></html>",
            "https://www.americannativeplants.com/my-account/",
        )

        self.assertFalse(ok)
        self.assertEqual([], reasons)

    def test_logged_in_signal_can_override_sitewide_recaptcha_script(self):
        ok, reasons = manual_login.evaluate_login_success(
            "<html><body><script src='recaptcha/api.js'></script><a>Log out</a></body></html>",
            "https://www.americannativeplants.com/my-account/",
        )

        self.assertTrue(ok)
        self.assertIn("text:log out", reasons)

    def test_prefill_login_fields_fills_but_does_not_submit(self):
        credential = Credential(
            supplier_id=43,
            url="https://www.americannativeplants.com/my-account/",
            user="buyer@example.com",
            password="real-password",
        )
        page = FakePage(
            fill_failures={
                "input[name='username']",
                "input[name='password']",
            }
        )

        result = manual_login.prefill_login_fields(page, credential)

        self.assertEqual(result["username_selector"], "input[type='email']")
        self.assertEqual(result["password_selector"], "input[type='password']")
        self.assertEqual(
            page.fill_calls,
            [
                ("input[name='username']", "buyer@example.com"),
                ("input[type='email']", "buyer@example.com"),
                ("input[name='password']", "real-password"),
                ("input[type='password']", "real-password"),
            ],
        )
        self.assertEqual(page.click_calls, [])

    def test_playwright_context_options_include_saved_storage_state(self):
        profile = stealth.BrowserProfile(
            user_agent="UA",
            viewport=(1440, 900),
            locale="en-US",
            timezone="America/New_York",
            accept_language="en-US,en;q=0.9",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "supplier_43.storage_state.json"
            storage_path.write_text(json.dumps({"cookies": []}))
            with mock.patch("scrape.core.fetcher.storage_state_path", return_value=storage_path):
                options = fetcher.build_playwright_context_options(profile, 43)

        self.assertEqual(options["storage_state"], str(storage_path))
        self.assertEqual(options["user_agent"], "UA")
        self.assertEqual(options["viewport"], {"width": 1440, "height": 900})


class FakePage:
    def __init__(self, fill_failures=None):
        self.fill_failures = set(fill_failures or [])
        self.fill_calls = []
        self.click_calls = []

    def fill(self, selector, value, timeout=0):
        self.fill_calls.append((selector, value))
        if selector in self.fill_failures:
            raise RuntimeError(f"missing selector: {selector}")

    def click(self, selector, timeout=0):
        self.click_calls.append(selector)


if __name__ == "__main__":
    unittest.main()
