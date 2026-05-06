import unittest
import csv
import json
import tempfile
from pathlib import Path

from tools.extract_dashboard_suppliers import SupplierExtractionError, load_dashboard_suppliers
from tools.audit_supplier_registry import (
    audit_raw_suppliers,
    collect_registered_adapters,
    validate_canonical_records,
)


ROOT = Path(__file__).resolve().parents[1]


class DashboardSupplierExtractionTests(unittest.TestCase):
    def test_extracts_dashboard_supplier_records_without_normalizing_fields(self):
        fixture = """
        <script>
        const S = [
          {id:244,n:"Blue Sky Nursery",city:"Lincoln",st:"ON",web:"blueskynursery.ca",cat:["Perennials","Shrubs"],d:{note:"keep raw"}},
          {id:244,n:"Blue Sky Nursery",city:"Lincoln",st:"ON",web:"blueskynursery.ca",cat:["Perennials","Shrubs"],d:{note:"duplicate row"}}
        ];
        </script>
        """
        with tempfile.TemporaryDirectory() as tmp:
            fixture_path = Path(tmp) / "index.html"
            fixture_path.write_text(fixture, encoding="utf-8")
            records = load_dashboard_suppliers(fixture_path)

        first = records[0]
        self.assertEqual(
            {
                "id": first["id"],
                "n": first["n"],
                "city": first["city"],
                "st": first["st"],
                "web": first["web"],
                "cat": first["cat"],
            },
            {
                "id": 244,
                "n": "Blue Sky Nursery",
                "city": "Lincoln",
                "st": "ON",
                "web": "blueskynursery.ca",
                "cat": ["Perennials", "Shrubs"],
            },
        )

        fields = {"id", "n", "city", "st", "web", "cat"}
        for record in records:
            self.assertTrue(fields.issubset(record), record)

    def test_raw_import_artifact_preserves_pre_canonical_dashboard_rows(self):
        raw_path = ROOT / "data" / "raw" / "current_dashboard_suppliers.json"
        records = json.loads(raw_path.read_text(encoding="utf-8"))

        self.assertEqual(127, len(records))
        first = records[0]
        self.assertEqual(1, first["id"])
        self.assertEqual("North Creek Nurseries", first["n"])
        self.assertEqual("Landenberg", first["city"])
        self.assertEqual("PA", first["st"])
        self.assertEqual("northcreeknurseries.com", first["web"])
        self.assertEqual(["Perennials", "Grasses", "Ferns", "Natives"], first["cat"])

    def test_current_dashboard_extraction_requires_explicit_canonical_opt_in(self):
        with self.assertRaises(SupplierExtractionError):
            load_dashboard_suppliers(ROOT / "index.html")

        dashboard_records = load_dashboard_suppliers(ROOT / "index.html", allow_canonical=True)
        canonical_records = json.loads(
            (ROOT / "data" / "master" / "suppliers.canonical.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(canonical_records), len(dashboard_records))
        self.assertEqual(
            {record["canonical_supplier_id"] for record in canonical_records},
            {record["canonicalId"] for record in dashboard_records},
        )


class SupplierRegistryAuditTests(unittest.TestCase):
    def test_reports_duplicate_missing_and_adapter_issues_with_codes(self):
        records = [
            {"id": 1, "n": "North Creek Nurseries", "city": "Landenberg", "st": "PA", "web": "northcreeknurseries.com"},
            {"id": 1, "n": "Kind Earth Growers", "city": "Ottsville", "st": "PA", "web": "kindearthgrowers.com"},
            {"id": 2, "n": "Cavano's Perennials", "city": "Kingsville", "st": "MD", "web": "cavanos.com"},
            {"id": 3, "n": "Babikow Greenhouses", "city": "Baltimore", "st": "MD", "web": "www.cavanos.com"},
            {"id": 4, "n": "Quality Greenhouses & Perennial Farm", "city": "Dillsburg", "st": "PA", "web": ""},
            {"id": 244, "n": "Blue Sky Nursery", "city": "", "st": "", "web": "blueskynursery.ca"},
        ]
        adapters = [
            {"supplier_id": 2, "supplier_name": "Cavano's Perennials", "placeholder": False},
            {"supplier_id": 16, "supplier_name": "Quality Greenhouses", "placeholder": False},
            {"supplier_id": 110, "supplier_name": "Walters Gardens", "placeholder": True},
            {"supplier_id": 244, "supplier_name": "SiteOne Landscape Supply", "placeholder": False},
        ]

        issues = audit_raw_suppliers(records, adapters)
        codes = {issue["code"] for issue in issues}

        self.assertIn("duplicate_legacy_id", codes)
        self.assertIn("duplicate_domain", codes)
        self.assertIn("missing_website", codes)
        self.assertIn("missing_location", codes)
        self.assertIn("adapter_without_supplier", codes)
        self.assertIn("supplier_without_adapter", codes)
        self.assertIn("registered_placeholder_adapter", codes)
        self.assertIn("name_domain_mismatch", codes)


class CanonicalSupplierRegistryTests(unittest.TestCase):
    def test_verified_canonical_records_have_unique_ids_domains_and_evidence(self):
        canonical_path = ROOT / "data" / "master" / "suppliers.canonical.json"
        records = json.loads(canonical_path.read_text(encoding="utf-8"))

        self.assertGreater(len(records), 0)
        issues = validate_canonical_records(records)
        self.assertEqual([], issues)

        for record in records:
            self.assertRegex(record["canonical_supplier_id"], r"^BB-SUP-\d{6}$")
            self.assertEqual("verified", record["verification_status"])
            self.assertTrue(record["evidence_urls"], record)
            self.assertTrue(record["verification_reason"], record)

    def test_adapter_map_covers_every_registered_adapter(self):
        map_path = ROOT / "data" / "master" / "adapter_supplier_map.csv"
        with map_path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))

        mapped_ids = {int(row["supplier_id"]) for row in rows}
        adapter_ids = {adapter.supplier_id for adapter in collect_registered_adapters()}
        self.assertEqual(adapter_ids, mapped_ids)

        for row in rows:
            self.assertIn(
                row["adapter_status"],
                {
                    "active_verified",
                    "active_unverified",
                    "placeholder_registered",
                    "disabled",
                    "none",
                },
            )
            self.assertTrue(row["canonical_supplier_id"] or row["quarantine_reason"], row)


if __name__ == "__main__":
    unittest.main()
