import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scrape import run


class NormalizeAdapterResultTests(unittest.TestCase):
    class LegacyAdapter:
        supplier_id = 244
        supplier_name = "Blue Sky Nursery"
        prefer_tier = "curl_cffi"

    def test_normalize_adapter_result_wraps_legacy_product_lists(self):
        legacy_products = [
            {"name": "Blue Fescue", "price": 12.5},
        ]

        normalized = run.normalize_adapter_result(self.LegacyAdapter(), legacy_products)

        self.assertEqual(normalized["supplier_id"], 244)
        self.assertEqual(normalized["supplier_name"], "Blue Sky Nursery")
        self.assertEqual(len(normalized["products"]), 1)
        self.assertEqual(normalized["products"][0]["supplier_id"], 244)
        self.assertEqual(
            normalized["products"][0]["supplier_name"],
            "Blue Sky Nursery",
        )


class PublishLiveFeedArtifactsTests(unittest.TestCase):
    def test_publish_live_feed_artifacts_preserves_existing_feed_on_empty_payload(self):
        payload = {
            "generated_at": "2026-04-22T20:00:00+00:00",
            "total_products": 0,
            "supplier_count": 0,
            "products": [],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "repo"
            output_dir = root / "scrape" / "output"
            output_dir.mkdir(parents=True)
            prices_path = output_dir / "prices.json"
            output_js_path = output_dir / "prices.js"
            root_js_path = root / "prices.js"
            prices_path.write_text('{"preserved": true}')
            output_js_path.write_text("window.LIVE_PRICES = {preserved: true};\n")
            root_js_path.write_text("window.LIVE_PRICES = {preserved: true};\n")

            result = run.publish_live_feed_artifacts(
                payload,
                output_dir=output_dir,
                root_dir=root,
                allow_empty=False,
            )

            self.assertFalse(result["published"])
            self.assertIn("preserve existing", result["reason"])
            self.assertEqual(prices_path.read_text(), '{"preserved": true}')
            self.assertIn("preserved", output_js_path.read_text())
            self.assertIn("preserved", root_js_path.read_text())

    def test_publish_live_feed_artifacts_writes_payload_when_products_exist(self):
        payload = {
            "generated_at": "2026-04-22T20:00:00+00:00",
            "total_products": 1,
            "supplier_count": 1,
            "products": [{"name": "Agave", "price": 19.99}],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "repo"
            output_dir = root / "scrape" / "output"
            output_dir.mkdir(parents=True)

            result = run.publish_live_feed_artifacts(
                payload,
                output_dir=output_dir,
                root_dir=root,
                allow_empty=False,
            )

            self.assertTrue(result["published"])
            written = json.loads((output_dir / "prices.json").read_text())
            self.assertEqual(written["total_products"], 1)
            self.assertIn("LIVE_PRICES", (output_dir / "prices.js").read_text())
            self.assertIn("LIVE_PRICES", (root / "prices.js").read_text())


class PreflightReportTests(unittest.TestCase):
    class PlaywrightAdapter:
        supplier_id = 16
        supplier_name = "Quality Greenhouses"
        prefer_tier = "playwright"

    class UndetectedAdapter:
        supplier_id = 207
        supplier_name = "SiteOne Landscape Supply"
        prefer_tier = "undetected"

    @mock.patch("scrape.run.collect_dependency_status")
    def test_build_preflight_report_flags_missing_browser_tiers(self, mock_status):
        mock_status.return_value = {
            "curl_cffi": True,
            "playwright": False,
            "undetected_chromedriver": False,
            "selenium": False,
            "pdfplumber": True,
            "openpyxl": True,
            "rich": True,
        }

        report = run.build_preflight_report(
            [self.PlaywrightAdapter, self.UndetectedAdapter]
        )

        self.assertFalse(report["tiers"]["playwright"]["available"])
        self.assertFalse(report["tiers"]["undetected"]["available"])
        self.assertEqual(report["tiers"]["playwright"]["suppliers"][0]["id"], 16)
        self.assertEqual(report["tiers"]["undetected"]["suppliers"][0]["id"], 207)


if __name__ == "__main__":
    unittest.main()
